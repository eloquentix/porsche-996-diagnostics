#!/usr/bin/env python3
"""Serve the isolated 996 design and relay pdiag diagnostics and confirmed emissions clearing.
Usage: python3 codex/serve.py [--port 8999]
"""
import argparse
import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = {'/api/status', '/api/live', '/api/ident', '/api/dtcs', '/api/over-rev', '/api/dme-live', '/api/capabilities', '/api/obd-dtcs'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        host = self.headers.get('Host', '')
        if host not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            return self.reply(403, b'{"error":"Forbidden host"}')
        if self.headers.get('Origin') != 'http://' + host or self.headers.get('X-Pdiag-Action') != 'clear-emissions-codes':
            return self.reply(403, b'{"error":"Same-origin confirmed requests only"}')
        if self.path != '/api/dtcs/clear':
            return self.reply(404, b'{"error":"Not found"}')
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply(415, b'{"error":"JSON required"}')
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError()
            body = self.rfile.read(length)
            payload = json.loads(body)
            if not isinstance(payload, dict) or payload.get('confirmed') is not True:
                raise ValueError()
        except ValueError:
            return self.reply(400, b'{"error":"Explicit JSON confirmation required"}')
        upstream = http.client.HTTPConnection('127.0.0.1', 8998, timeout=40)
        try:
            upstream.request('POST', '/api/dtcs/clear', body=body, headers={
                'Host': '127.0.0.1:8998', 'Origin': 'http://127.0.0.1:8998',
                'Content-Type': 'application/json', 'X-Pdiag-Action': 'clear-emissions-codes'})
            response = upstream.getresponse()
            self.reply(response.status, response.read(), response.getheader('Content-Type', 'application/json'))
        except (OSError, http.client.HTTPException):
            self.reply(502, b'{"error":"The backend connection failed. The outcome may be unknown; read the codes again. This request will not be retried.","kind":"outcome_unknown"}')
        finally:
            upstream.close()

    def do_GET(self):
        port = self.server.server_port
        if self.headers.get('Host') not in (f'127.0.0.1:{port}', f'localhost:{port}'):
            return self.reply(403, b'{"error":"Forbidden host"}')
        path = self.path.split('?', 1)[0]
        if path in ('/', '/dashboard-996.html'):
            return self.reply(200, (ROOT / 'dashboard-996.html').read_bytes(), 'text/html; charset=utf-8')
        if path == '/favicon.ico':
            return self.reply(204, b'')
        if path not in API:
            return self.reply(404, b'{"error":"Not found"}')
        upstream = http.client.HTTPConnection('127.0.0.1', 8998, timeout=40)
        started = False
        try:
            upstream.request('GET', path, headers={'Host': '127.0.0.1:8998'})
            response = upstream.getresponse()
            streaming = response.getheader('Content-Type', '').startswith('text/event-stream')
            if not streaming:
                return self.reply(response.status, response.read(), response.getheader('Content-Type', 'application/json'))
            self.send_response(response.status)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            started = True
            while line := response.readline():
                self.wfile.write(line)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (OSError, http.client.HTTPException) as error:
            body = json.dumps({'error': 'Cannot reach pdiag on port 8998.', 'kind': 'connection'}).encode()
            if started:
                try:
                    self.wfile.write(b'data: ' + body + b'\n\n')
                    self.wfile.flush()
                except OSError:
                    pass
            else:
                self.reply(502, body)
        finally:
            upstream.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8999)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.daemon_threads = True
    print(f'996 dashboard: http://127.0.0.1:{args.port}/#live', flush=True)
    print(f'Design preview: http://127.0.0.1:{args.port}/?demo=1#live', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
