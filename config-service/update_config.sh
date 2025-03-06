#!/bin/bash

# Default values
SERVER="localhost:5000"
BACKEND_TYPE="etcd"
PORTS="[100, 200, 300]"

# Help message
function show_help {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -s, --server    Server address (default: localhost:5000)"
    echo "  -b, --backend   Backend type (default: etcd)"
    echo "  -p, --ports     Control plane ports as JSON array (default: [100, 200, 300])"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -b redis -p '[100, 200, 400]'"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -s|--server)
            SERVER="$2"
            shift 2
            ;;
        -b|--backend)
            BACKEND_TYPE="$2"
            shift 2
            ;;
        -p|--ports)
            PORTS="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Create the JSON configuration
CONFIG="{\"backend_type\": \"$BACKEND_TYPE\", \"control_plane_ports\": $PORTS}"

echo "Updating configuration on $SERVER with:"
echo "$CONFIG"

# Send the PUT request to update the configuration
RESPONSE=$(curl -s -X PUT -H "Content-Type: application/json" -d "$CONFIG" "http://$SERVER/updateConfig/")

echo "Server response: $RESPONSE"
