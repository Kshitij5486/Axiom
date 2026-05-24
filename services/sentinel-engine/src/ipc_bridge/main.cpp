#include "../../include/ingress_handler.h"
#include "../../include/flow_tracker.h"
#include "../../include/sni_extractor.h"
#include "../../include/ipc_bridge.h"
#include <pcap.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <net/ethernet.h>
#include <iostream>
#include <csignal>
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>

#define ETH_HDR_LEN 14
#define SOCKET_PATH "/tmp/axiom_sentinel.sock"

static bool g_running = true;
void sig_handler(int) { g_running = false; }

// Thread-safe event queue
std::queue<FlowEvent>    g_queue;
std::mutex               g_mutex;
std::condition_variable  g_cv;

void sender_thread(IPCBridge& bridge) {
    while (g_running) {
        std::unique_lock<std::mutex> lock(g_mutex);
        g_cv.wait_for(lock, std::chrono::milliseconds(100),
                      []{ return !g_queue.empty(); });

        while (!g_queue.empty()) {
            FlowEvent evt = g_queue.front();
            g_queue.pop();
            lock.unlock();
            bridge.send(evt);
            lock.lock();
        }
    }
}

int main(int argc, char* argv[]) {
    std::signal(SIGINT, sig_handler);
    std::string iface = (argc > 1) ? argv[1] : "eth0";
    std::string sock  = (argc > 2) ? argv[2] : SOCKET_PATH;

    std::cout << "[SENTINEL] IPC Bridge Service v1.0\n";
    std::cout << "[SENTINEL] Socket: " << sock << "\n";

    FlowTracker tracker;
    IPCBridge   bridge(sock);

    // Try to connect (non-fatal if Go isn't running yet)
    bridge.connect();

    // Start sender thread
    std::thread sender(sender_thread, std::ref(bridge));

    // Capture loop
    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t* handle = pcap_open_live(iface.c_str(), 65535, 1, 1000, errbuf);
    if (!handle) {
        std::cerr << "[SENTINEL] Cannot open " << iface << ": " << errbuf << "\n";
        g_running = false;
        sender.join();
        return 1;
    }

    struct bpf_program fp;
    pcap_compile(handle, &fp, "tcp port 443", 0, PCAP_NETMASK_UNKNOWN);
    pcap_setfilter(handle, &fp);
    pcap_freecode(&fp);

    std::cout << "[SENTINEL] Capturing on " << iface << "\n";

    pcap_pkthdr* header;
    const uint8_t* pkt;
    int res;

    while (g_running && (res = pcap_next_ex(handle, &header, &pkt)) >= 0) {
        if (res == 0) continue;
        if (header->caplen < (size_t)(ETH_HDR_LEN + 20 + 20)) continue;

        const uint8_t* ip_hdr = pkt + ETH_HDR_LEN;
        const struct ip* iph  = reinterpret_cast<const struct ip*>(ip_hdr);
        if (iph->ip_v != 4 || iph->ip_p != IPPROTO_TCP) continue;

        int ip_len = iph->ip_hl * 4;
        const struct tcphdr* tcph =
            reinterpret_cast<const struct tcphdr*>(ip_hdr + ip_len);
        int tcp_len = tcph->th_off * 4;

        const uint8_t* payload = ip_hdr + ip_len + tcp_len;
        size_t pay_len = header->caplen - ETH_HDR_LEN - ip_len - tcp_len;

        char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &iph->ip_src, src, INET_ADDRSTRLEN);
        inet_ntop(AF_INET, &iph->ip_dst, dst, INET_ADDRSTRLEN);

        FlowEvent evt;
        evt.src_ip   = src;
        evt.src_port = ntohs(tcph->th_sport);
        evt.dst_ip   = dst;
        evt.dst_port = ntohs(tcph->th_dport);
        evt.protocol = "TCP";
        evt.timestamp = header->ts.tv_sec;
        evt.status   = "NEW_FLOW";

        if (pay_len >= 5) {
            std::string sni = extract_sni(payload, pay_len);
            if (!sni.empty()) {
                evt.sni_domain = sni;
                evt.status     = "SNI_EXTRACTED";
                std::cout << "[IPC_BRIDGE] " << src << " -> " << dst
                          << " SNI=" << sni << "\n";
            }
        }

        tracker.update(evt);

        // Push to sender queue
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            g_queue.push(evt);
        }
        g_cv.notify_one();
    }

    g_running = false;
    sender.join();
    pcap_close(handle);
    return 0;
}
