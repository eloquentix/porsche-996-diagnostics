"""Opt-in OBD Mode 04 support, kept outside the original read-only project.

User-authorized exception, 2026-11-08: add backend code to reset fault codes.
Scope: standard emissions DTCs / related diagnostic information only.
No clearing command is sent at startup, by GET, or by any live stream.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from pathlib import Path

from pdiag import obd, web
from pdiag.transport import KLineError

ROOT = Path(__file__).resolve().parent
CONFIRM_HEADER = 'clear-emissions-codes'
CLEAR_PATH = '/api/dtcs/clear'


class ClearError(Exception):
    def __init__(self, message, status=409, kind='precondition'):
        super().__init__(message)
        self.status, self.kind = status, kind


def append_audit(path, entry):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        data = (json.dumps({'t': time.time(), **entry}) + '\n').encode()
        while data:
            data = data[os.write(fd, data):]
        os.fsync(fd)
    finally:
        os.close(fd)


class ClearService:
    """Use the same Car lock and link as live reads. Never open a second cable."""
    def __init__(self, car, audit_path=ROOT / 'logs' / 'clear-codes.jsonl'):
        self.car, self.audit_path = car, audit_path
        self.requests = {}
        self.request_lock = threading.Lock()

    def clear(self, payload):
        if not isinstance(payload, dict) or payload.get('confirmed') is not True:
            raise ClearError('Explicit confirmation is required.', 400, 'confirmation')
        request_id = payload.get('request_id')
        if not isinstance(request_id, str) or not re.fullmatch(r'[a-zA-Z0-9-]{16,80}', request_id):
            raise ClearError('A unique request_id is required.', 400, 'request_id')
        with self.request_lock:
            if request_id in self.requests:
                raise ClearError('This request was already handled. Read the codes again before starting a new request.', 409, 'duplicate')
            # Reserve before touching the bus; uncertain requests are never retried.
            self.requests[request_id] = time.monotonic()
            self.requests = {k: v for k, v in self.requests.items() if time.monotonic() - v < 86400}
        return self.car._guard(lambda: self._clear_locked(request_id))

    def _clear_locked(self, request_id):
        car = self.car
        link = car._obd()
        # Fresh values on this link, never cached UI readings.
        rpm = obd.read_pid(link, 0x0C)[0]
        speed = obd.read_pid(link, 0x0D)[0]
        if not all(isinstance(v, (int, float)) and math.isfinite(v) and v == 0 for v in (rpm, speed)):
            raise ClearError('No codes were cleared. Park the car, switch the engine off, and leave the ignition on.')
        before = obd.read_stored_dtcs(link)
        readiness_before = obd.read_pid(link, 0x01)[0]
        record = {'request_id': request_id, 'mode': 'mock' if car.mock else 'hardware',
                  'scope': 'emissions', 'before': before, 'readiness_before': readiness_before}
        # If a snapshot cannot be saved, fail before the clearing command.
        append_audit(self.audit_path, {**record, 'phase': 'before'})
        try:
            replies = link.request(b'\x04', settle=obd.DTC_SETTLE)
        except KLineError as error:
            self._log_result({**record, 'phase': 'unconfirmed', 'detail': str(error)})
            raise ClearError('The clearing command was sent, but no valid acknowledgment was received. Its outcome is unknown. Read the codes again; do not assume they were cleared.', 502, 'outcome_unknown') from error
        acknowledgments = sum(r == b'\x44' for r in replies)
        rejected = any(len(r) >= 3 and r[:2] == b'\x7f\x04' for r in replies)
        if not acknowledgments:
            kind = 'rejected' if rejected else 'outcome_unknown'
            self._log_result({**record, 'phase': kind, 'replies': [r.hex() for r in replies]})
            raise ClearError('The ECU rejected code clearing.' if rejected else 'No clear acknowledgment was received. Read the codes again to determine their state.', 502, kind)
        # Mode 04 invalidates cached status/readiness. Refresh it on the next scan.
        car._latest = {}
        car._static_due = 0.0
        result = {'acknowledged': True, 'scope': 'emissions', 'before': before,
                  'remaining': None, 'verified': False, 'partial_response': rejected,
                  'request_id': request_id}
        try:
            result['remaining'] = obd.read_stored_dtcs(link)
            result['monitor_status'] = obd.read_pid(link, 0x01)[0]
            result['verified'] = not rejected
        except KLineError as error:
            result['verification_error'] = str(error)
        result['cleared'] = result['verified'] and not result['remaining']
        if result['cleared']:
            result['message'] = 'Clearing was acknowledged. No stored emissions codes were returned by the follow-up scan.'
        elif result['remaining']:
            result['message'] = 'Clearing was acknowledged, but emissions codes are still present: ' + ', '.join(result['remaining']) + '.'
        else:
            result['message'] = 'Clearing was acknowledged, but verification is incomplete. Read the codes again.'
        result['audit_saved'] = self._log_result({**record, 'phase': 'result', 'result': result})
        return result

    def _log_result(self, record):
        try:
            append_audit(self.audit_path, record)
            return True
        except OSError:
            return False


def make_extended_handler(car, audit_path=ROOT / 'logs' / 'clear-codes.jsonl'):
    base = web.make_handler(car)
    service = ClearService(car, audit_path)

    class Handler(base):
        def _valid_host(self):
            port = self.server.server_port
            return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

        def do_GET(self):
            if not self._valid_host():
                return self._json(403, {'error': 'Forbidden host'})
            path = self.path.split('?', 1)[0]
            if path == '/api/capabilities':
                return self._json(200, {'clear_emissions_codes': True, 'clear_path': CLEAR_PATH,
                                        'odometer': False, 'backend': '996-extension-v1'})
            if path == '/api/obd-dtcs':
                return self._api(lambda: car._guard(lambda: {'codes': obd.read_stored_dtcs(car._obd()), 'scope': 'emissions'}))
            return super().do_GET()

        def do_POST(self):
            if not self._valid_host():
                return self._json(403, {'error': 'Forbidden host'})
            expected_origin = 'http://' + self.headers.get('Host', '')
            if self.headers.get('Origin') != expected_origin or self.headers.get('X-Pdiag-Action') != CONFIRM_HEADER:
                return self._json(403, {'error': 'Same-origin confirmed requests only'})
            if self.path != CLEAR_PATH:
                return self._json(404, {'error': 'Not found'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self._json(415, {'error': 'JSON required'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError('Invalid body length')
                payload = json.loads(self.rfile.read(length))
            except (ValueError, json.JSONDecodeError):
                return self._json(400, {'error': 'Invalid request body'})
            try:
                self._json(200, service.clear(payload))
            except ClearError as error:
                self._json(error.status, {'error': str(error), 'kind': error.kind})
            except KLineError as error:
                self._json(502, {'error': 'Could not complete the pre-clear checks: ' + str(error), 'kind': 'kline'})
            except OSError:
                self._json(500, {'error': 'Could not save the pre-clear snapshot. No clearing command was sent.', 'kind': 'audit'})
    return Handler
