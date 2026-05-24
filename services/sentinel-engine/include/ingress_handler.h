#pragma once
#include <pcap.h>
#include <string>
#include <functional>
#include "../src/common/flow_data.h"

class IngressHandler {
public:
    using PacketCallback = std::function<void(const FlowEvent&)>;
    explicit IngressHandler(const std::string& iface, PacketCallback cb);
    ~IngressHandler();
    bool start();
    void stop();
    int packets_captured() const { return packets_captured_; }
private:
    pcap_t*        handle_;
    std::string    interface_;
    PacketCallback callback_;
    int            packets_captured_;
    bool           running_;
    static void packet_handler(u_char* user,
                               const struct pcap_pkthdr* hdr,
                               const u_char* pkt);
    void process_packet(const struct pcap_pkthdr* hdr, const u_char* pkt);
};
