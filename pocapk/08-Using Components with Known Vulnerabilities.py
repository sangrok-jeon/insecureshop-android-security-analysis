from http.server import BaseHTTPRequestHandler, HTTPServer

class MyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)

        print("[+] POST received")
        print("    path:", self.path)
        print("    length:", content_length)
        print("    content-type:", self.headers.get("Content-Type"))

        with open("exfiltrated_file.bin", "wb") as f:
            f.write(body)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        return

server = HTTPServer(("0.0.0.0", 8080), MyHandler)
print("[*] Listening on 0.0.0.0:8080")
server.serve_forever()
