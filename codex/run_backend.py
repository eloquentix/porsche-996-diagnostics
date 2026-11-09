#!/usr/bin/env python3
"""Start pdiag with the separate, confirmed emissions-code clearing endpoint.
Uses the original CLI and transport; no original source files are changed.
Example:
  uv run python codex/run_backend.py \
    --port /dev/cu.usbserial-AG0KJ4N5 ui --car '996 Targa' --http-port 8998 --no-browser
"""
import signal
import sys
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'src'))
from pdiag import cli, web
from clear_backend import ROOT, make_extended_handler
cli.LOG_DIR = ROOT / 'logs'


def serve_extended(car, host='127.0.0.1', port=8998, open_browser=False):
    server = ThreadingHTTPServer((host, port), make_extended_handler(car))
    server.daemon_threads = True
    def shutdown(*args):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown)
    print(f'pdiag with confirmed emissions clearing: http://{host}:{port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    web.serve = serve_extended
    cli.main()
