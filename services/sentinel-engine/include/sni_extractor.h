#pragma once
#include <string>
#include <cstdint>

// Extracts SNI domain from TLS ClientHello payload
// Returns empty string if not found or parse fails
std::string extract_sni(const uint8_t* payload, size_t len);

// Returns true if this TCP payload looks like a TLS ClientHello
bool is_tls_client_hello(const uint8_t* payload, size_t len);
