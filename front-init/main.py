import socket
import threading
import json
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

HTTP_PORT = 3000
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
STORAGE_DIR = "storage"
STORAGE_FILE = os.path.join(STORAGE_DIR, "data.json")


os.makedirs(STORAGE_DIR, exist_ok=True)


if not os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, 'w') as f:
        json.dump({}, f)

def save_to_json(data):
    with open(STORAGE_FILE, 'r+') as f:
        current_data = json.load(f)
        current_data.update(data)
        f.seek(0)
        json.dump(current_data, f, indent=2)

def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', 5000)
    sock.bind(server_address)
    
    print("UDP server listening on port 5000")
    
    while True:
        data, address = sock.recvfrom(4096)
        if data:
            message = json.loads(data.decode('utf-8'))
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            save_to_json({timestamp: message})

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        path = pr_url.path
        if path == '/':
            self.send_html_file('index.html')
        elif path == '/message.html':
            self.send_html_file('message.html')
        elif path == '/style.css':
            self.send_static_file('style.css', 'text/css')
        elif path == '/logo.png':
            self.send_static_file('logo.png', 'image/png')
        else:
            self.send_html_file('error.html', 404)

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            username = params.get('username', [''])[0]
            message = params.get('message', [''])[0]
            
            if username and message:
                data = json.dumps({"username": username, "message": message})
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(data.encode('utf-8'), ('localhost', 5000))
                self.send_response(302)
                self.send_header('Location', '/message.html')
                self.end_headers()
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Both 'username' and 'message' fields are required")
        else:
            self.send_error(404)

    def send_html_file(self, filename, status=200):
        try:
            file_path = os.path.join(STATIC_DIR, filename)
            with open(file_path, 'rb') as f:
                self.send_response(status)
                if filename.endswith('.html'):
                    self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(404)

    def send_static_file(self, filename, content_type):
        try:
            file_path = os.path.join(STATIC_DIR, filename)
            with open(file_path, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(404)

def run_http_server():
    server_address = ('', HTTP_PORT)
    http = HTTPServer(server_address, HttpHandler)
    print(f"Starting HTTP server on port {HTTP_PORT}...")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()

if __name__ == '__main__':
    udp_thread = threading.Thread(target=udp_server)
    udp_thread.daemon = True
    udp_thread.start()
    
    run_http_server()


