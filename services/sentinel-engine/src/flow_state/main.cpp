#include "../../include/flow_tracker.h"
#include "../../include/ingress_handler.h"
#include <iostream>
#include <csignal>
#include <thread>
#include <chrono>

static bool g_running = true;
void sig_handler(int) { g_running = false; }

int main(int argc, char* argv[]) {
    std::signal(SIGINT, sig_handler);
    std::string iface = (argc > 1) ? argv[1] : "eth0";

    std::cout << "[SENTINEL] Flow State Service v1.0\n";

    FlowTracker tracker;

    // GC thread — runs every 30 seconds
    std::thread gc_thread([&](){
        while (g_running) {
            std::this_thread::sleep_for(std::chrono::seconds(30));
            tracker.garbage_collect(120);
            std::cout << "[SENTINEL] Active flows: "
                      << tracker.active_count()
                      << " | Total seen: "
                      << tracker.total_seen() << std::endl;
        }
    });
    gc_thread.detach();

    auto on_pkt = [&](const FlowEvent& evt) {
        tracker.update(evt);
    };

    IngressHandler handler(iface, on_pkt);
    if (!handler.start()) {
        std::cerr << "[SENTINEL] Failed. Run: sudo ./flow_service\n";
        return 1;
    }

    std::cout << "[SENTINEL] Total flows seen: "
              << tracker.total_seen() << std::endl;
    return 0;
}
