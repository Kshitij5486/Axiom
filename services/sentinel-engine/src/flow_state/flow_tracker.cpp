#include "../../include/flow_tracker.h"
#include <iostream>
#include <algorithm>

FlowTracker::FlowTracker() : total_seen_(0) {}

FlowKey FlowTracker::make_key(const FlowEvent& evt) const {
    // Normalise: always put lower IP first so both directions map to same key
    FlowKey k;
    if (evt.src_ip < evt.dst_ip ||
       (evt.src_ip == evt.dst_ip && evt.src_port <= evt.dst_port)) {
        k.src_ip   = evt.src_ip;
        k.src_port = evt.src_port;
        k.dst_ip   = evt.dst_ip;
        k.dst_port = evt.dst_port;
    } else {
        k.src_ip   = evt.dst_ip;
        k.src_port = evt.dst_port;
        k.dst_ip   = evt.src_ip;
        k.dst_port = evt.src_port;
    }
    k.protocol = evt.protocol;
    return k;
}

TCPState FlowTracker::infer_state(const FlowEvent& evt) const {
    if (evt.status == "SYN")     return TCPState::SYN_SEEN;
    if (evt.status == "FIN")     return TCPState::FIN_SEEN;
    if (evt.status == "CLOSED")  return TCPState::CLOSED;
    return TCPState::ESTABLISHED;
}

void FlowTracker::update(const FlowEvent& evt) {
    std::lock_guard<std::mutex> lock(mutex_);
    total_seen_++;

    FlowKey key = make_key(evt);
    auto now    = std::chrono::steady_clock::now();

    auto it = flows_.find(key);
    if (it == flows_.end()) {
        // New flow
        FlowRecord rec;
        rec.key          = key;
        rec.state        = infer_state(evt);
        rec.packet_count = 1;
        rec.byte_count   = 0;
        rec.sni_domain   = evt.sni_domain;
        rec.last_seen    = now;
        rec.sni_extracted = !evt.sni_domain.empty();
        flows_[key]      = rec;

        std::cout << "[FLOW_TRACKER] NEW "
                  << key.src_ip << ":" << key.src_port
                  << " -> "
                  << key.dst_ip << ":" << key.dst_port;
        if (!evt.sni_domain.empty())
            std::cout << " SNI=" << evt.sni_domain;
        std::cout << std::endl;
    } else {
        // Existing flow — update
        it->second.packet_count++;
        it->second.last_seen = now;

        // Update SNI if we now have it
        if (!evt.sni_domain.empty() && !it->second.sni_extracted) {
            it->second.sni_domain    = evt.sni_domain;
            it->second.sni_extracted = true;
            std::cout << "[FLOW_TRACKER] SNI_UPDATE "
                      << key.src_ip << ":" << key.src_port
                      << " SNI=" << evt.sni_domain << std::endl;
        }

        // Update state machine
        TCPState new_state = infer_state(evt);
        if (new_state == TCPState::FIN_SEEN ||
            new_state == TCPState::CLOSED) {
            it->second.state = new_state;
        }
    }
}

std::vector<FlowRecord> FlowTracker::get_active_flows() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<FlowRecord> result;
    result.reserve(flows_.size());
    for (auto& [k, v] : flows_) {
        if (v.state != TCPState::CLOSED)
            result.push_back(v);
    }
    return result;
}

int FlowTracker::garbage_collect(int timeout_seconds) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto now     = std::chrono::steady_clock::now();
    int  removed = 0;

    for (auto it = flows_.begin(); it != flows_.end(); ) {
        auto age = std::chrono::duration_cast<std::chrono::seconds>(
            now - it->second.last_seen).count();

        if (age > timeout_seconds ||
            it->second.state == TCPState::CLOSED) {
            it = flows_.erase(it);
            removed++;
        } else {
            ++it;
        }
    }

    if (removed > 0)
        std::cout << "[FLOW_TRACKER] GC removed " << removed
                  << " stale flows. Active: " << flows_.size() << std::endl;
    return removed;
}

size_t FlowTracker::active_count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return flows_.size();
}
