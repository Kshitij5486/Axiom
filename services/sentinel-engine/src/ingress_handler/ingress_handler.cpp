#include "../../include/ingress_handler.h"
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <net/ethernet.h>
#include <arpa/inet.h>
#include <iostream>
#include <chrono>

#define ETH_HDR_LEN 14

IngressHandler::IngressHandler(const std::string& iface, PacketCallback cb)
    : handle_(nullptr), interface_(iface), callback_(cb),
      packets_captured_(0), running_(false) {}

IngressHandler::~IngressHandler() { stop(); }

bool IngressHandler::start() {
    char errbuf[PCAP_ERRBUF_SIZE];
    handle_ = pcap_open_live(interface_.c_str(), 65535, 1, 1000, errbuf);
    if (!handle_) {
        std::cerr << "[SENTINEL] Cannot open " << interface_
                  << ": " << errbuf << std::endl;
        return false;
    }
    struct bpf_program fp;
    const char* filter = "tcp port 443";
    if (pcap_compile(handle_, &fp, filter, 0, PCAP_NETMASK_UNKNOWN) == -1 ||
        pcap_setfilter(handle_, &fp) == -1) {
        std::cerr << "[SENTINEL] BPF filter failed: "
                  << pcap_geterr(handle_) << std::endl;
        pcap_freecode(&fp);
        return false;
    }
    pcap_freecode(&fp);
    running_ = true;
    std::cout << "[SENTINEL] Listening on " << interface_
              << " (filter: " << filter << ")" << std::endl;
    pcap_loop(handle_, 0, packet_handler, reinterpret_cast<u_char*>(this));
    return true;
}

void IngressHandler::stop() {
    if (handle_) {
        running_ = false;
        pcap_breakloop(handle_);
        pcap_close(handle_);
        handle_ = nullptr;
    }
}

void IngressHandler::packet_handler(u_char* user,
                                     const struct pcap_pkthdr* hdr,
                                     const u_char* pkt) {
    reinterpret_cast<IngressHandler*>(user)->process_packet(hdr, pkt);
}

void IngressHandler::process_packet(const struct pcap_pkthdr* hdr,
                                     const u_char* pkt) {
    packets_captured_++;
    if (hdr->caplen < ETH_HDR_LEN + sizeof(struct ip)) return;

    const u_char* ip_hdr = pkt + ETH_HDR_LEN;
    const struct ip* iph = reinterpret_cast<const struct ip*>(ip_hdr);
    if (iph->ip_v != 4) return;

    int ip_len = iph->ip_hl * 4;
    if (ip_len < 20 || iph->ip_p != IPPROTO_TCP) return;

    const struct tcphdr* tcph =
        reinterpret_cast<const struct tcphdr*>(ip_hdr + ip_len);

    FlowEvent evt;
    evt.timestamp = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &iph->ip_src, src, INET_ADDRSTRLEN);
    inet_ntop(AF_INET, &iph->ip_dst, dst, INET_ADDRSTRLEN);

    evt.src_ip   = src;
    evt.dst_ip   = dst;
    evt.src_port = ntohs(tcph->th_sport);
    evt.dst_port = ntohs(tcph->th_dport);
    evt.protocol = "TCP";
    evt.status   = "NEW_FLOW";
    evt.sni_domain = "";

    if (callback_) callback_(evt);
}
