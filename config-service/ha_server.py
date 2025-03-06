from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

# Path to the configuration file
CONFIG_FILE = 'config.json'

class ConfigHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/getConfig/':
            try:
                # Read the latest configuration data from file
                with open(CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
                
                # Set response headers
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                # Send the JSON response
                self.wfile.write(json.dumps(config_data).encode())
                print(f"Configuration served: {config_data}")
            except Exception as e:
                # Handle errors gracefully
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error reading configuration: {str(e)}".encode())
                print(f"Error serving configuration: {str(e)}")
        else:
            # Return 404 for any other paths
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    # Add a PUT handler to update the configuration
    def do_PUT(self):
        if self.path == '/updateConfig/':
            try:
                # Get the content length
                content_length = int(self.headers['Content-Length'])
                
                # Read the request body
                post_data = self.rfile.read(content_length).decode('utf-8')
                
                # Parse the JSON data
                new_config = json.loads(post_data)
                
                # Validate the config has the required fields
                if 'backend_type' not in new_config or 'control_plane_ports' not in new_config:
                    self.send_response(400)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Invalid configuration format')
                    return
                
                # Write the new configuration to file
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(new_config, f, indent=2)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Configuration updated successfully')
                print(f"Configuration updated to: {new_config}")
            except Exception as e:
                # Handle errors gracefully
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error updating configuration: {str(e)}".encode())
                print(f"Error updating configuration: {str(e)}")
        else:
            # Return 404 for any other paths
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def run_server(host='0.0.0.0', port=5000):
    # Ensure the config file exists before starting
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "backend_type": "etcd",
            "control_plane_ports": [100, 200, 300]
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default configuration file: {CONFIG_FILE}")
    
    server_address = (host, port)
    httpd = HTTPServer(server_address, ConfigHandler)
    print(f"Starting HA configuration server on {host}:{port}")
    print(f"Configuration is stored in {CONFIG_FILE} and can be updated without server restart")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
