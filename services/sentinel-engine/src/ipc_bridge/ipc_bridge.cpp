#include "../../include/ipc_bridge.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <cstring>

// ── JSON serialisation (no external library needed) ──
std::string escape_json(const std::string& s) {
    std::ostringstream o;
    for (char c : s) {
        if      (c == '"')  o << "\\\"";
        else if (c == '\\') o << "\\\\";
        else if (c == '\n') o << "\\n";
        else                o << c;
    }
    return o.str();
}

std::string flow_event_to_json(const FlowEvent& e) {
    std::ostringstream j;
    j << "{"
      << "\"timestamp\":"  << e.timestamp          << ","
      << "\"src_ip\":\""   << escape_json(e.src_ip) << "\","
      << "\"src_port\":"   << e.src_port            << ","
      << "\"dest_ip\":\""  << escape_json(e.dst_ip) << "\","
      << "\"dest_port\":"  << e.dst_port            << ","
      << "\"protocol\":\"" << escape_json(e.protocol)   << "\","
      << "\"sni_domain\":\"" << escape_json(e.sni_domain) << "\","
      << "\"status\":\""   << escape_json(e.status) << "\""
      << "}\n";           // newline delimiter for Go scanner
    return j.str();
}

// ── IPCBridge implementation ──
IPCBridge::IPCBridge(const std::string& path)
    : socket_path_(path), fd_(-1) {}

IPCBridge::~IPCBridge() { disconnect(); }

bool IPCBridge::connect() {
    fd_ = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd_ < 0) {
        std::cerr << "[IPC] socket() failed: " << strerror(errno) << "\n";
        return false;
    }

    struct sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socket_path_.c_str(), sizeof(addr.sun_path)-1);

    if (::connect(fd_, reinterpret_cast<struct sockaddr*>(&addr),
                  sizeof(addr)) < 0) {
        std::cerr << "[IPC] connect() to " << socket_path_
                  << " failed: " << strerror(errno)
                  << " (is Go control plane running?)\n";
        close(fd_);
        fd_ = -1;
        return false;
    }

    std::cout << "[IPC] Connected to " << socket_path_ << "\n";
    return true;
}

bool IPCBridge::send(const FlowEvent& evt) {
    if (fd_ < 0) {
        // Try reconnect once
        if (!reconnect()) return false;
    }

    std::string json = flow_event_to_json(evt);
    ssize_t written = write(fd_, json.c_str(), json.size());

    if (written < 0) {
        std::cerr << "[IPC] write() failed: " << strerror(errno) << "\n";
        disconnect();
        return false;
    }
    return true;
}

void IPCBridge::disconnect() {
    if (fd_ >= 0) {
        close(fd_);
        fd_ = -1;
        std::cout << "[IPC] Disconnected\n";
    }
}

bool IPCBridge::reconnect() {
    disconnect();
    std::cout << "[IPC] Attempting reconnect to " << socket_path_ << "\n";
    return connect();
}
