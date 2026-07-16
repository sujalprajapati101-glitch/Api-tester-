import json
import time
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import requests as req_lib
import requests 


os.chdir(os.path.dirname(os.path.abspath(__file__)))


class APIProxyHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/proxy":
            self._handle_proxy()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        if self.path == "/proxy":
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_error(404)

    def _handle_proxy(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request_data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        url = request_data.get("url", "")
        method = request_data.get("method", "GET").upper()
        headers = request_data.get("headers", {})
        body_data = request_data.get("body", None)
        timeout = request_data.get("timeout", 30)

        if not url:
            self._send_json(400, {"error": "URL is required"})
            return

        try:
            start = time.time()

            kwargs = {
                "headers": headers,
                "timeout": timeout,
                "allow_redirects": True,
                "verify": True,
            }

            if body_data is not None:
                if isinstance(body_data, dict) or isinstance(body_data, list):
                    kwargs["json"] = body_data
                elif isinstance(body_data, str) and body_data.strip():
                    try:
                        kwargs["json"] = json.loads(body_data)
                    except json.JSONDecodeError:
                        kwargs["data"] = body_data.encode("utf-8")
                else:
                    kwargs["data"] = body_data.encode("utf-8") if isinstance(body_data, str) else body_data

            response = req_lib.request(method, url, **kwargs)
            elapsed = round((time.time() - start) * 1000, 2)

            resp_headers = dict(response.headers)
            resp_body = response.text

            content_type = resp_headers.get("Content-Type", "")
            parsed_body = resp_body
            if "json" in content_type:
                try:
                    parsed_body = json.loads(resp_body)
                except json.JSONDecodeError:
                    pass

            result = {
                "status": response.status_code,
                "statusText": response.reason,
                "headers": resp_headers,
                "body": parsed_body,
                "time": elapsed,
                "size": len(response.content),
            }

            self._send_json(200, result)

        except req_lib.exceptions.Timeout:
            self._send_json(504, {"error": "Request timed out"})
        except req_lib.exceptions.ConnectionError as e:
            self._send_json(502, {"error": f"Connection error: {str(e)}"})
        except req_lib.exceptions.RequestException as e:
            self._send_json(500, {"error": f"Request failed: {str(e)}"})
        except Exception as e:
            self._send_json(500, {"error": f"Server error: {str(e)}"})

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")


def main():
    port = int(os.environ.get("PORT", 3000))
    server = HTTPServer(("0.0.0.0", port), APIProxyHandler)
    print(f"\n  API Tester running at http://localhost:{port}\n")
    print(f"  Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
