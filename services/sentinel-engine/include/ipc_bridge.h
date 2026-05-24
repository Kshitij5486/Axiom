#pragma once
#include <string>
#include "../src/common/flow_data.h"

std::string flow_event_to_json(const FlowEvent& evt);

class IPCBridge {
public:
    explicit IPCBridge(const std::string& socket_path);
    ~IPCBridge();
    bool connect();
    bool send(const FlowEvent& evt);
    void disconnect();
    bool is_connected() const { return fd_ >= 0; }
private:
    std::string socket_path_;
    int         fd_;
    bool reconnect();
};
