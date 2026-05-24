#include "../../include/sni_extractor.h"
#include <cstring>
#include <arpa/inet.h>

// TLS record layer constants
static const uint8_t TLS_CONTENT_HANDSHAKE = 0x16;
static const uint8_t TLS_HANDSHAKE_CLIENT_HELLO = 0x01;
static const uint8_t TLS_EXT_SNI = 0x00; // Extension type 0x0000

bool is_tls_client_hello(const uint8_t* p, size_t len) {
    // Minimum: TLS record (5) + handshake header (4) + client hello (34+)
    if (len < 43) return false;
    // TLS record type must be 0x16 (handshake)
    if (p[0] != TLS_CONTENT_HANDSHAKE) return false;
    // TLS version: 0x03 0x01 (TLS 1.0) to 0x03 0x04 (TLS 1.3)
    if (p[1] != 0x03 || p[2] < 0x01 || p[2] > 0x04) return false;
    // Handshake type must be 0x01 (ClientHello)
    if (p[5] != TLS_HANDSHAKE_CLIENT_HELLO) return false;
    return true;
}

std::string extract_sni(const uint8_t* p, size_t len) {
    if (!is_tls_client_hello(p, len)) return "";

    // Safe pointer arithmetic helper
    // pos tracks current parse position
    size_t pos = 5; // skip TLS record header (5 bytes)

    // Handshake header: type(1) + length(3)
    if (pos + 4 > len) return "";
    pos += 4; // skip handshake header

    // ClientHello:
    // client_version(2) + random(32) = 34 bytes
    if (pos + 34 > len) return "";
    pos += 34;

    // Session ID: length(1) + data
    if (pos + 1 > len) return "";
    uint8_t session_id_len = p[pos++];
    if (pos + session_id_len > len) return "";
    pos += session_id_len;

    // Cipher suites: length(2) + data
    if (pos + 2 > len) return "";
    uint16_t cipher_len = (p[pos] << 8) | p[pos+1];
    pos += 2;
    if (pos + cipher_len > len) return "";
    pos += cipher_len;

    // Compression methods: length(1) + data
    if (pos + 1 > len) return "";
    uint8_t comp_len = p[pos++];
    if (pos + comp_len > len) return "";
    pos += comp_len;

    // Extensions: total length(2)
    if (pos + 2 > len) return "";
    uint16_t ext_total = (p[pos] << 8) | p[pos+1];
    pos += 2;

    size_t ext_end = pos + ext_total;
    if (ext_end > len) return "";

    // Iterate extensions looking for SNI (type 0x0000)
    while (pos + 4 <= ext_end) {
        uint16_t ext_type = (p[pos] << 8) | p[pos+1];
        uint16_t ext_len  = (p[pos+2] << 8) | p[pos+3];
        pos += 4;

        if (pos + ext_len > ext_end) break;

        if (ext_type == 0x0000) {
            // SNI extension found
            // SNI list length(2) + entry type(1) + name length(2) + name
            if (ext_len < 5) break;
            size_t sni_pos = pos;
            // uint16_t sni_list_len = (p[sni_pos] << 8) | p[sni_pos+1];
            sni_pos += 2;
            uint8_t name_type = p[sni_pos++]; // 0 = host_name
            if (name_type != 0x00) break;
            uint16_t name_len = (p[sni_pos] << 8) | p[sni_pos+1];
            sni_pos += 2;
            if (sni_pos + name_len > pos + ext_len) break;
            // Extract domain string
            return std::string(reinterpret_cast<const char*>(p + sni_pos),
                               name_len);
        }
        pos += ext_len;
    }
    return "";
}
