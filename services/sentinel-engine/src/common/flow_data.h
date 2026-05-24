#pragma once
#include <string>
#include <cstdint>
#include <chrono>

struct FlowKey {
    std::string src_ip;
    uint16_t    src_port;
    std::string dst_ip;
    uint16_t    dst_port;
    std::string protocol;
    bool operator==(const FlowKey& o) const {
        return src_ip==o.src_ip && src_port==o.src_port &&
               dst_ip==o.dst_ip && dst_port==o.dst_port &&
               protocol==o.protocol;
    }
};

struct FlowKeyHash {
    std::size_t operator()(const FlowKey& k) const {
        std::size_t h=0;
        auto mix=[&](std::size_t v){ h^=v+0x9e3779b9+(h<<6)+(h>>2); };
        mix(std::hash<std::string>{}(k.src_ip));
        mix(std::hash<uint16_t>{}(k.src_port));
        mix(std::hash<std::string>{}(k.dst_ip));
        mix(std::hash<uint16_t>{}(k.dst_port));
        mix(std::hash<std::string>{}(k.protocol));
        return h;
    }
};

enum class TCPState { SYN_SEEN, ESTABLISHED, FIN_SEEN, CLOSED };

struct FlowRecord {
    FlowKey   key;
    TCPState  state;
    uint64_t  packet_count;
    uint64_t  byte_count;
    std::string sni_domain;
    std::chrono::steady_clock::time_point last_seen;
    bool      sni_extracted;
};

struct FlowEvent {
    uint64_t    timestamp;
    std::string src_ip;
    uint16_t    src_port;
    std::string dst_ip;
    uint16_t    dst_port;
    std::string protocol;
    std::string sni_domain;
    std::string status;
};
