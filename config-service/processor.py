import sys
import json

def process_backend(backend_type, control_plane_ports):
    # Process the backend type
    if backend_type == "etcd":
        print("This is from ETCD")
    elif backend_type.lower() == "redis":
        print("Redis is here baby")
    else:
        print("We don't support that backend yet")
    
    # Print the list of control plane ports
    print(f"Control plane ports: {control_plane_ports}")

if __name__ == "__main__":
    # Check if we have at least 2 arguments (script name + backend type + ports json)
    if len(sys.argv) < 3:
        print("Usage: python processor.py <backend_type> '<control_plane_ports_json>'")
        sys.exit(1)
    
    backend_type = sys.argv[1]
    
    # Parse the control plane ports from the JSON string
    try:
        control_plane_ports = json.loads(sys.argv[2])
    except json.JSONDecodeError:
        print("Error: Invalid JSON format for control plane ports")
        sys.exit(1)
    
    process_backend(backend_type, control_plane_ports)
