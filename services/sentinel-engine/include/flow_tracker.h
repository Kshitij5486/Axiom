#pragma once
#include <unordered_map>
#include <vector>
#include <mutex>
#include <chrono>
#include "../src/common/flow_data.h"

class FlowTracker {
public:
    FlowTracker();

    // Process an incoming flow event — update or create flow record
    void update(const FlowEvent& evt);

    // Get all currently active flows
    std::vector<FlowRecord> get_active_flows() const;

    // Remove flows inactive for more than timeout_seconds
    int garbage_collect(int timeout_seconds = 120);

    // Stats
    size_t active_count() const;
    size_t total_seen()   const { return total_seen_; }

private:
    mutable std::mutex                                    mutex_;
    std::unordered_map<FlowKey, FlowRecord, FlowKeyHash> flows_;
    size_t                                               total_seen_;

    FlowKey make_key(const FlowEvent& evt) const;
    TCPState infer_state(const FlowEvent& evt) const;
};
