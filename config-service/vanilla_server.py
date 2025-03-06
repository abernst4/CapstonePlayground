from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class ConfigHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/getConfig/':
            # Configuration data to be returned
            config_data = {
                "backend_type": "etcd",  # Can be changed to "redis" or something else
                "control_plane_ports": [100, 200, 300]
            }
            
            # Set response headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Send the JSON response
            self.wfile.write(json.dumps(config_data).encode())
        else:
            # Return 404 for any other paths
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    # Silence the default log messages
    def log_message(self, format, *args):
        pass

def run_server(host='0.0.0.0', port=5000):
    server_address = (host, port)
    httpd = HTTPServer(server_address, ConfigHandler)
    print(f"Starting configuration server on {host}:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
