#include "../../include/ingress_handler.h"
#include "../../include/flow_tracker.h"
#include "../../include/sni_extractor.h"
#include <pcap.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <net/ethernet.h>
#include <iostream>
#include <csignal>

#define ETH_HDR_LEN 14

static bool g_running = true;
void sig_handler(int) { g_running = false; }

int main(int argc, char* argv[]) {
    std::signal(SIGINT, sig_handler);
    std::string iface = (argc > 1) ? argv[1] : "eth0";

    std::cout << "[SENTINEL] Protocol Inspector v1.0\n";
    std::cout << "[SENTINEL] TLS/SNI extractor active\n";

    FlowTracker tracker;

    auto on_pkt = [&](const FlowEvent& base_evt) {
        // We need raw packet access for SNI — re-capture via pcap handle
        // For now update tracker with base event
        tracker.update(base_evt);
    };

    // Custom capture loop with SNI extraction
    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t* handle = pcap_open_live(iface.c_str(), 65535, 1, 1000, errbuf);
    if (!handle) {
        std::cerr << "[SENTINEL] Cannot open " << iface << ": " << errbuf << "\n";
        return 1;
    }

    struct bpf_program fp;
    pcap_compile(handle, &fp, "tcp port 443", 0, PCAP_NETMASK_UNKNOWN);
    pcap_setfilter(handle, &fp);
    pcap_freecode(&fp);

    std::cout << "[SENTINEL] Listening on " << iface << "\n";

    pcap_pkthdr* header;
    const uint8_t* pkt;
    int res;

    while (g_running && (res = pcap_next_ex(handle, &header, &pkt)) >= 0) {
        if (res == 0) continue; // timeout

        if (header->caplen < (size_t)(ETH_HDR_LEN + 20 + 20)) continue;

        const uint8_t* ip_hdr  = pkt + ETH_HDR_LEN;
        const struct ip* iph   = reinterpret_cast<const struct ip*>(ip_hdr);
        if (iph->ip_v != 4 || iph->ip_p != IPPROTO_TCP) continue;

        int ip_len = iph->ip_hl * 4;
        const struct tcphdr* tcph =
            reinterpret_cast<const struct tcphdr*>(ip_hdr + ip_len);
        int tcp_len = tcph->th_off * 4;

        // TCP payload starts after IP + TCP headers
        const uint8_t* payload = ip_hdr + ip_len + tcp_len;
        size_t payload_len = header->caplen - ETH_HDR_LEN - ip_len - tcp_len;

        if (payload_len < 5) continue;

        // Try SNI extraction
        std::string sni = extract_sni(payload, payload_len);

        if (!sni.empty()) {
            char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &iph->ip_src, src, INET_ADDRSTRLEN);
            inet_ntop(AF_INET, &iph->ip_dst, dst, INET_ADDRSTRLEN);

            std::cout << "[SNI] " << src << ":" << ntohs(tcph->th_sport)
                      << " -> " << dst << ":" << ntohs(tcph->th_dport)
                      << " | domain=" << sni << "\n";

            // Build enriched event for tracker
            FlowEvent evt;
            evt.src_ip     = src;
            evt.src_port   = ntohs(tcph->th_sport);
            evt.dst_ip     = dst;
            evt.dst_port   = ntohs(tcph->th_dport);
            evt.protocol   = "TCP";
            evt.sni_domain = sni;
            evt.status     = "SNI_EXTRACTED";
            evt.timestamp  = header->ts.tv_sec;
            tracker.update(evt);
        }
    }

    pcap_close(handle);
    std::cout << "[SENTINEL] Active flows: " << tracker.active_count() << "\n";
    return 0;
}
