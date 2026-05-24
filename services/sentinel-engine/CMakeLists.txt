cmake_minimum_required(VERSION 3.10)
project(SentinelEngine VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_library(PCAP_LIBRARY pcap REQUIRED)
find_path(PCAP_INCLUDE_DIR pcap.h REQUIRED)

include_directories(
    ${PCAP_INCLUDE_DIR}
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/src/common
)

# Shared ingress handler object (reused by flow_service)
add_library(ingress_lib OBJECT
    src/ingress_handler/ingress_handler.cpp
)
target_include_directories(ingress_lib PUBLIC ${PCAP_INCLUDE_DIR} include src/common)

# Target 1: ingress_service
add_executable(ingress_service
    src/ingress_handler/main.cpp
    $<TARGET_OBJECTS:ingress_lib>
)
target_link_libraries(ingress_service ${PCAP_LIBRARY} pthread)

# Target 2: flow_service
add_executable(flow_service
    src/flow_state/main.cpp
    src/flow_state/flow_tracker.cpp
    $<TARGET_OBJECTS:ingress_lib>
)
target_link_libraries(flow_service ${PCAP_LIBRARY} pthread)

# Target 3: inspec_service
add_executable(inspec_service
    src/protocol_inspec/main.cpp
    src/protocol_inspec/sni_extractor.cpp
    $<TARGET_OBJECTS:ingress_lib>
)
target_link_libraries(inspec_service ${PCAP_LIBRARY} pthread)

# Target 4: ipc_service
add_executable(ipc_service
    src/ipc_bridge/main.cpp
    src/ipc_bridge/ipc_bridge.cpp
    $<TARGET_OBJECTS:ingress_lib>
)
target_link_libraries(ipc_service ${PCAP_LIBRARY} pthread)
