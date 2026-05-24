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

add_executable(ingress_service
    src/ingress_handler/main.cpp
    src/ingress_handler/ingress_handler.cpp
)
target_link_libraries(ingress_service ${PCAP_LIBRARY} pthread)

add_executable(flow_service
    src/flow_state/main.cpp
    src/flow_state/flow_tracker.cpp
)
target_link_libraries(flow_service ${PCAP_LIBRARY} pthread)

add_executable(inspec_service
    src/protocol_inspec/main.cpp
    src/protocol_inspec/sni_extractor.cpp
)
target_link_libraries(inspec_service ${PCAP_LIBRARY} pthread)

add_executable(ipc_service
    src/ipc_bridge/main.cpp
    src/ipc_bridge/ipc_bridge.cpp
)
target_link_libraries(ipc_service ${PCAP_LIBRARY} pthread)
