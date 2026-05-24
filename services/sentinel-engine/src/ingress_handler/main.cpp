#include "../../include/ingress_handler.h"
#include <iostream>
#include <csignal>

static bool g_running = true;
void sig_handler(int) { g_running = false; }

int main(int argc, char* argv[]) {
    std::signal(SIGINT, sig_handler);
    std::signal(SIGTERM, sig_handler);

    std::string iface = (argc > 1) ? argv[1] : "eth0";
    std::cout << "[SENTINEL] Axiom Sentinel Ingress v1.0\n";
    std::cout << "[SENTINEL] Interface: " << iface << "\n";

    auto on_pkt = [](const FlowEvent& e) {
        std::cout << "[FLOW] " << e.src_ip << ":" << e.src_port
                  << " -> " << e.dst_ip << ":" << e.dst_port
                  << " ts=" << e.timestamp << "\n";
    };

    IngressHandler h(iface, on_pkt);
    if (!h.start()) {
        std::cerr << "[SENTINEL] Failed. Run: sudo ./ingress_service\n";
        return 1;
    }
    return 0;
}
