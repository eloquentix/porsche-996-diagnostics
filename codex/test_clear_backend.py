import io
import json
import sys
import time
from email.message import Message
from types import SimpleNamespace

import pytest
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'src'))
from pdiag.service import Car
from pdiag.mock import MockCar
from pdiag.transport import NoResponse
import clear_backend as backend


class Link:
    def __init__(self, rpm=0, speed=0, response=None, verify_error=False, remaining=False):
        self.rpm, self.speed = rpm, speed
        self.response = [b'\x44'] if response is None else response
        self.verify_error, self.remaining = verify_error, remaining
        self.sent = []
        self.cleared = False

    def request(self, data, **kwargs):
        self.sent.append(data)
        if data == b'\x01\x0c': return [b'\x41\x0c' + round(self.rpm * 4).to_bytes(2, 'big')]
        if data == b'\x01\x0d': return [b'\x41\x0d' + bytes([self.speed])]
        if data == b'\x01\x01': return [b'\x41\x01\x00\x07\x00\x00']
        if data == b'\x03':
            if self.cleared and self.verify_error: raise NoResponse('Verification timed out')
            return [b'\x43\x03\x00\x00\x00' if not self.cleared or self.remaining else b'\x43\x00\x00']
        if data == b'\x04':
            self.cleared = True
            if isinstance(self.response, Exception): raise self.response
            return self.response
        raise AssertionError(data)


def make_service(tmp_path, **options):
    car = Car(MockCar(), mock=True)
    link = Link(**options)
    car.link = link
    car._last_io = time.monotonic()
    car._latest = {'rpm': 500, 'monitor_status': 'old'}
    return backend.ClearService(car, tmp_path / 'audit.jsonl'), link


def payload(n=1): return {'confirmed': True, 'request_id': f'test-confirmed-{n:08d}'}


def test_clear_snapshot_acknowledgment_and_verification(tmp_path):
    service, link = make_service(tmp_path)
    result = service.clear(payload())
    assert result['cleared'] and result['verified']
    assert result['before'] == ['P0300'] and result['remaining'] == []
    assert link.sent.count(b'\x04') == 1
    assert link.sent[:4] == [b'\x01\x0c', b'\x01\x0d', b'\x03', b'\x01\x01']
    assert service.car._latest == {} and service.car._static_due == 0
    records = [json.loads(x) for x in (tmp_path / 'audit.jsonl').read_text().splitlines()]
    assert [r['phase'] for r in records] == ['before', 'result']


@pytest.mark.parametrize('options', [{'rpm': 900}, {'speed': 1}])
def test_engine_running_or_moving_never_clears(tmp_path, options):
    service, link = make_service(tmp_path, **options)
    with pytest.raises(backend.ClearError, match='Park the car'): service.clear(payload())
    assert b'\x04' not in link.sent


@pytest.mark.parametrize('body', [{}, {'confirmed': False}, {'confirmed': 'true'}, {'confirmed': True}, None])
def test_requires_exact_confirmation_and_request_id(tmp_path, body):
    service, link = make_service(tmp_path)
    with pytest.raises(backend.ClearError): service.clear(body)
    assert not link.sent


def test_duplicate_does_not_send_again(tmp_path):
    service, link = make_service(tmp_path)
    service.clear(payload())
    with pytest.raises(backend.ClearError, match='already handled'): service.clear(payload())
    assert link.sent.count(b'\x04') == 1


@pytest.mark.parametrize('response,kind', [(NoResponse('timeout'),'outcome_unknown'), ([b'\x43'],'outcome_unknown'), ([b'\x7f\x04\x22'],'rejected')])
def test_no_false_success_and_no_automatic_retry(tmp_path, response, kind):
    service, link = make_service(tmp_path, response=response)
    with pytest.raises(backend.ClearError) as error: service.clear(payload())
    assert error.value.kind == kind
    assert link.sent.count(b'\x04') == 1


@pytest.mark.parametrize('options', [{'verify_error': True}, {'remaining': True}, {'response': [b'\x44', b'\x7f\x04\x22']}])
def test_partial_verification_never_reports_cleared(tmp_path, options):
    service, link = make_service(tmp_path, **options)
    result = service.clear(payload())
    assert result['acknowledged'] and not result['cleared']


def test_audit_failure_prevents_write(tmp_path, monkeypatch):
    service, link = make_service(tmp_path)
    def fail(*args): raise OSError('No disk space')
    monkeypatch.setattr(backend, 'append_audit', fail)
    with pytest.raises(OSError): service.clear(payload())
    assert b'\x04' not in link.sent


class ParkedMock(MockCar):
    def __init__(self, generic):
        super().__init__(generic=generic)
        self.erased = False
    def _obd(self, data):
        if data == b'\x01\x0c': return b'\x41\x0c\x00\x00'
        if data == b'\x01\x0d': return b'\x41\x0d\x00'
        if data == b'\x04': self.erased = True; return b'\x44'
        if data == b'\x03' and self.erased: return b'\x43\x00\x00'
        return super()._obd(data)


@pytest.mark.parametrize('protocol', ['iso9141', 'kwp'])
def test_real_protocol_stack_against_simulated_parked_car(tmp_path, protocol):
    transport = ParkedMock(protocol)
    car = Car(transport, mock=True)
    result = backend.ClearService(car, tmp_path / 'audit.jsonl').clear(payload())
    assert result['cleared'] and transport.erased


def call_handler(tmp_path, method, path, headers, body=b''):
    service, link = make_service(tmp_path)
    cls = backend.make_extended_handler(service.car, tmp_path / 'http-audit.jsonl')
    handler = object.__new__(cls)
    handler.server = SimpleNamespace(server_port=8998)
    handler.headers = Message()
    for k, v in headers.items(): handler.headers[k] = v
    handler.path, handler.rfile = path, io.BytesIO(body)
    results = []
    handler._json = lambda status, result: results.append((status, result))
    getattr(handler, method)()
    return results[0], link


@pytest.mark.parametrize('extra', [{}, {'Origin': 'http://evil.test'}, {'Origin': 'http://127.0.0.1:8998'}])
def test_http_refuses_unconfirmed_or_cross_origin_writes(tmp_path, extra):
    body = json.dumps(payload()).encode()
    result, link = call_handler(tmp_path, 'do_POST', backend.CLEAR_PATH, {'Host': '127.0.0.1:8998', 'Content-Type': 'application/json', 'Content-Length': str(len(body)), **extra}, body)
    assert result[0] == 403 and b'\x04' not in link.sent


def test_confirmed_http_path(tmp_path):
    body = json.dumps(payload()).encode()
    result, link = call_handler(tmp_path, 'do_POST', backend.CLEAR_PATH, {'Host': '127.0.0.1:8998', 'Origin': 'http://127.0.0.1:8998', 'X-Pdiag-Action': backend.CONFIRM_HEADER, 'Content-Type': 'application/json', 'Content-Length': str(len(body))}, body)
    assert result[0] == 200 and result[1]['cleared']


def test_capabilities_is_read_only(tmp_path):
    result, link = call_handler(tmp_path, 'do_GET', '/api/capabilities', {'Host': '127.0.0.1:8998'})
    assert result[1]['clear_emissions_codes'] and not link.sent
