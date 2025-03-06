#!/bin/bash

# Get the port this script is running on (passed as an argument)
CURRENT_PORT=$1

if [ -z "$CURRENT_PORT" ]; then
    echo "Usage: $0 <port_number>"
    exit 1
fi

# Call the configuration server to get the config
CONFIG_RESPONSE=$(curl -s http://config-server:5000/getConfig/)

# Extract the backend type and ports using jq
BACKEND_TYPE=$(echo $CONFIG_RESPONSE | jq -r '.backend_type')
CONTROL_PLANE_PORTS=$(echo $CONFIG_RESPONSE | jq -r '.control_plane_ports')

echo "Retrieved backend type: $BACKEND_TYPE"
echo "Retrieved control plane ports: $CONTROL_PLANE_PORTS"

# Check if the current port is in the control plane
if echo $CONTROL_PLANE_PORTS | jq -e ". | contains([$CURRENT_PORT])" > /dev/null; then
    echo "I am apart of the control plane"
else
    echo "I am not part of the control plane"
fi

# Call the second Python program with the backend type and ports
echo "Calling processor with backend type: $BACKEND_TYPE"
python3 /app/processor.py "$BACKEND_TYPE" "$CONTROL_PLANE_PORTS"
