"""Offline public-source capture boundaries using synthetic responses only."""
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import ssl
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import public_source_snapshot as snapshot


class FakeResponse:
    def __init__(self, body=b'', status=200, content_type='text/html; charset=utf-8',
                 headers=None):
        self.status = status
        self.headers = [('Content-Type', content_type)] + list(headers or [])
        self.stream = io.BytesIO(body)

    def getheaders(self):
        return list(self.headers)

    def getheader(self, name, default=None):
        return next((value for key, value in self.headers if key.lower() == name.lower()),
                    default)

    def read(self, size=-1):
        return self.stream.read(size)


class PublicSourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.output = self.base / 'capture'
        # A missed mock must fail offline, never contact a real host.
        self.network_guard = patch('socket.create_connection',
                                   side_effect=AssertionError('Unexpected live connection'))
        self.network_guard.start()
        self.addCleanup(self.network_guard.stop)
        self.socket_guard = patch('socket.socket',
                                  side_effect=AssertionError('Unexpected live socket'))
        self.socket_guard.start()
        self.addCleanup(self.socket_guard.stop)
        self.dns_guard = patch('socket.getaddrinfo',
                               side_effect=AssertionError('Unexpected live DNS'))
        self.dns_guard.start()
        self.addCleanup(self.dns_guard.stop)

    def capture_response(self, response, url='https://www.foxtons.co.uk/properties/test',
                         output=None):
        connection = Mock()
        with patch.object(snapshot, '_resolve_public', return_value=['93.184.216.34']) as resolve:
            with patch.object(snapshot, '_open_response',
                              return_value=(connection, response)) as open_response:
                receipt = snapshot.capture(url, output or self.output)
        return receipt, resolve, open_response, connection

    def assert_receipt(self, receipt, output=None):
        output = output or self.output
        persisted = json.loads((output / 'receipt.json').read_text(encoding='utf-8'))
        self.assertEqual({key: value for key, value in receipt.items()
                          if key not in ('receipt_path', 'receipt_sha256')}, persisted)
        self.assertEqual(output / 'receipt.json', Path(receipt['receipt_path']))
        self.assertEqual(hashlib.sha256((output / 'receipt.json').read_bytes()).hexdigest(),
                         receipt['receipt_sha256'])
        self.assertEqual(2, receipt['version'])
        self.assertEqual(2 * 1024 * 1024, receipt['max_body_bytes'])
        self.assertIn('declared_content_length', receipt)
        if receipt['status'] is None:
            self.assertIsNone(receipt['declared_content_length'])
        self.assertEqual('independent_host_capture_after_actor', receipt['role'])
        self.assertIs(receipt['source_claims_verified'], False)
        self.assertIsInstance(receipt['captured_at'], str)
        self.assertTrue(receipt['captured_at'])
        self.assertEqual(0o700, stat.S_IMODE(output.stat().st_mode))
        for path in output.rglob('*'):
            self.assertEqual(0o700 if path.is_dir() else 0o600,
                             stat.S_IMODE(path.stat().st_mode), str(path))
        for key in ('body', 'text'):
            descriptor = receipt.get(key)
            if descriptor is not None:
                path = output / descriptor['path']
                self.assertEqual(output, path.parent)
                raw = path.read_bytes()
                self.assertEqual(len(raw), descriptor['bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), descriptor['sha256'])

    def test_allowed_hosts_capture_visible_text_and_private_hash_receipts(self):
        body = (b'<!doctype html><html><head><style>hidden-style</style>'
                b'<script>hidden-script</script></head><body><h1>One &amp; two</h1>'
                b'<p>Home <span>near</span> station.</p>'
                b'<script>raise SystemExit("never execute")</script></body></html>')
        for index, host in enumerate(('www.foxtons.co.uk', 'www.graingerplc.co.uk',
                                      'prod.graingerplc.co.uk', 'www.getliving.com',
                                      'www.fizzyliving.com')):
            with self.subTest(host=host):
                output = self.base / ('capture-%d' % index)
                url = 'https://' + host + '/homes/example?view=details'
                receipt, resolve, opened, connection = self.capture_response(
                    FakeResponse(body, headers=[('Content-Length', str(len(body)))]), url, output)
                self.assertIs(receipt['ok'], True)
                self.assertEqual(200, receipt['status'])
                self.assertEqual(len(body), receipt['declared_content_length'])
                self.assertEqual(url, receipt['requested_url'])
                self.assertIs(receipt['body']['complete'], True)
                self.assertEqual(body, (output / receipt['body']['path']).read_bytes())
                text = (output / receipt['text']['path']).read_text(encoding='utf-8')
                self.assertIn('One & two', text)
                self.assertIn('Home near station.', ' '.join(text.split()))
                self.assertNotIn('hidden-script', text)
                self.assertNotIn('hidden-style', text)
                self.assertNotIn('SystemExit', text)
                resolve.assert_called_once_with(host)
                self.assertEqual(1, opened.call_count)
                self.assertEqual((host, '/homes/example?view=details', '93.184.216.34'),
                                 opened.call_args.args[:3])
                self.assertGreater(opened.call_args.args[3], 0)
                self.assertLessEqual(opened.call_args.args[3], 10)
                connection.close.assert_called_once()
                self.assert_receipt(receipt, output)

    def test_unsafe_urls_fail_before_dns_or_connect(self):
        urls = (
            'http://www.foxtons.co.uk/example',
            'https://foxtons.co.uk/example',
            'https://www.foxtons.co.uk.attacker.example/example',
            'https://www.foxtons.co.uk@attacker.example/example',
            'https://user:secret@www.foxtons.co.uk/example',
            'https://www.foxtons.co.uk:8443/example',
            'https://127.0.0.1/example',
            'https://[::1]/example',
            'https://www.foxtons.co.uk./example',
            None,
            42,
            {'source': 'https://www.foxtons.co.uk/example'},
        )
        with patch.object(snapshot, '_resolve_public') as resolve:
            with patch.object(snapshot, '_open_response') as opened:
                for index, url in enumerate(urls):
                    with self.subTest(url=url):
                        output = self.base / ('rejected-%d' % index)
                        receipt = snapshot.capture(url, output)
                        self.assertIs(receipt['ok'], False)
                        self.assertTrue(receipt['error'])
                        self.assertIsNone(receipt['status'])
                        self.assertIsNone(receipt['body'])
                        self.assertIsNone(receipt['text'])
                        if not isinstance(url, str):
                            self.assertIsNone(receipt['requested_url'])
                        self.assert_receipt(receipt, output)
        resolve.assert_not_called()
        opened.assert_not_called()

    def test_any_nonpublic_dns_answer_rejects_entire_resolution(self):
        for index, address in enumerate(('127.0.0.1', '10.0.0.1', '169.254.169.254',
                                         '0.0.0.0', '224.0.0.1', '::1', 'fe80::1',
                                         'fc00::1', '::ffff:127.0.0.1')):
            with self.subTest(address=address):
                family = socket.AF_INET6 if ':' in address else socket.AF_INET
                answers = [
                    (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '',
                     ('93.184.216.34', 443)),
                    (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, '',
                     (address, 443, 0, 0) if family == socket.AF_INET6 else (address, 443)),
                ]
                with patch('socket.getaddrinfo', return_value=answers):
                    with patch.object(snapshot, '_open_response') as opened:
                        output = self.base / ('dns-rejected-%d' % index)
                        receipt = snapshot.capture('https://www.foxtons.co.uk/example', output)
                opened.assert_not_called()
                self.assertIs(receipt['ok'], False)
                self.assertTrue(receipt['error'])
                self.assertIsNone(receipt['body'])
                self.assert_receipt(receipt, output)

    def test_resolution_and_connection_failures_leave_honest_receipts(self):
        for phase in ('resolve', 'connect'):
            with self.subTest(phase=phase):
                output = self.base / phase
                with patch.object(snapshot, '_resolve_public',
                                  side_effect=socket.gaierror('synthetic DNS failure')
                                  if phase == 'resolve' else None,
                                  return_value=['93.184.216.34']):
                    with patch.object(snapshot, '_open_response',
                                      side_effect=TimeoutError('synthetic timeout')) as opened:
                        receipt = snapshot.capture('https://www.foxtons.co.uk/example', output)
                self.assertEqual(0 if phase == 'resolve' else 1, opened.call_count)
                self.assertIs(receipt['ok'], False)
                self.assertIsNone(receipt['status'])
                self.assertTrue(receipt['error'])
                self.assertIsNone(receipt['body'])
                self.assertIsNone(receipt['text'])
                self.assert_receipt(receipt, output)

    def test_redirect_retains_raw_without_following_or_extracting(self):
        body = b'<html><body>Redirect response, not the destination.</body></html>'
        receipt, resolve, opened, connection = self.capture_response(
            FakeResponse(body, status=302,
                         headers=[('Location', 'http://169.254.169.254/latest/meta-data/')]))
        self.assertIs(receipt['ok'], False)
        self.assertEqual(302, receipt['status'])
        self.assertTrue(receipt['error'])
        self.assertIsNone(receipt['text'])
        self.assertEqual(body, (self.output / receipt['body']['path']).read_bytes())
        self.assertEqual(1, resolve.call_count)
        self.assertEqual(1, opened.call_count)
        connection.close.assert_called_once()
        self.assert_receipt(receipt)

    def test_oversized_response_is_capped_and_not_presented_as_complete_text(self):
        cap = 2 * 1024 * 1024
        body = b'<html><body>' + b'x' * cap + b'</body></html>'
        receipt, unused_resolve, opened, connection = self.capture_response(
            FakeResponse(body, headers=[('Content-Length', str(len(body)))]))
        self.assertIs(receipt['ok'], False)
        self.assertEqual(200, receipt['status'])
        self.assertTrue(receipt['error'])
        self.assertIs(receipt['body']['complete'], False)
        self.assertEqual(cap, receipt['body']['bytes'])
        self.assertEqual(len(body), receipt['declared_content_length'])
        self.assertIsNone(receipt['text'])
        self.assertEqual(body[:cap], (self.output / receipt['body']['path']).read_bytes())
        self.assertEqual(1, opened.call_count)
        connection.close.assert_called_once()
        self.assert_receipt(receipt)

    def test_non_html_retains_only_raw_bytes(self):
        body = b'%PDF-1.7\x00\xff\n<html><p>This is not an HTML document.</p></html>'
        receipt, unused_resolve, unused_opened, connection = self.capture_response(
            FakeResponse(body, content_type='application/pdf'))
        self.assertIs(receipt['ok'], False)
        self.assertEqual(200, receipt['status'])
        self.assertTrue(receipt['error'])
        self.assertIs(receipt['body']['complete'], True)
        self.assertIsNone(receipt['text'])
        self.assertEqual(body, (self.output / receipt['body']['path']).read_bytes())
        connection.close.assert_called_once()
        self.assert_receipt(receipt)

    def test_existing_or_symlink_destinations_are_rejected_without_network(self):
        existing = self.base / 'existing'
        existing.mkdir()
        sentinel = existing / 'keep.txt'
        sentinel.write_text('unchanged', encoding='utf-8')
        linked = self.base / 'linked'
        linked.symlink_to(existing, target_is_directory=True)
        dangling = self.base / 'dangling'
        dangling.symlink_to(self.base / 'missing', target_is_directory=True)
        with patch.object(snapshot, '_resolve_public') as resolve:
            with patch.object(snapshot, '_open_response') as opened:
                for output in (existing, sentinel, linked, dangling, linked / 'child'):
                    with self.subTest(output=str(output)):
                        with self.assertRaises(ValueError):
                            snapshot.capture('https://www.foxtons.co.uk/example', output)
        resolve.assert_not_called()
        opened.assert_not_called()
        self.assertEqual('unchanged', sentinel.read_text(encoding='utf-8'))
        self.assertEqual(['keep.txt'], sorted(path.name for path in existing.iterdir()))
        self.assertFalse((self.base / 'missing').exists())

    def test_transport_pins_numeric_ip_tls_hostname_and_single_credential_free_get(self):
        context = Mock(verify_mode=ssl.CERT_REQUIRED, check_hostname=True)
        plain_socket = Mock()
        wrapped_socket = context.wrap_socket.return_value
        trust = SimpleNamespace(openssl_cafile='/synthetic/system-ca.pem', openssl_capath=None)
        with patch.object(snapshot.ssl, 'get_default_verify_paths', return_value=trust):
            with patch.object(snapshot.os.path, 'isfile', return_value=True):
                with patch.object(snapshot.os.path, 'isdir', return_value=False):
                    with patch.object(snapshot.ssl, 'SSLContext', return_value=context) as tls:
                        connection = snapshot._PinnedHTTPSConnection(
                            'www.foxtons.co.uk', '93.184.216.34', 10)
        tls.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations.assert_called_once_with(
            cafile='/synthetic/system-ca.pem', capath=None)
        with patch('socket.socket', return_value=plain_socket) as create_socket:
            connection.connect()
        create_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        plain_socket.connect.assert_called_once_with(('93.184.216.34', 443))
        context.wrap_socket.assert_called_once_with(plain_socket,
                                                    server_hostname='www.foxtons.co.uk')
        self.assertIs(connection.sock, wrapped_socket)
        self.assertEqual(2, plain_socket.settimeout.call_count)
        for call in plain_socket.settimeout.call_args_list:
            self.assertGreater(call.args[0], 0)
            self.assertLessEqual(call.args[0], 10)

        transport = Mock()
        environment = {'HTTPS_PROXY': 'https://proxy.invalid',
                       'HTTP_PROXY': 'http://proxy.invalid',
                       'ALL_PROXY': 'socks5://proxy.invalid',
                       'SSL_CERT_FILE': '/synthetic/untrusted-ca.pem',
                       'NETRC': '/synthetic/credentials'}
        with patch.dict(os.environ, environment):
            with patch.object(snapshot, '_PinnedHTTPSConnection', return_value=transport) as pinned:
                returned, response = snapshot._open_response(
                    'www.foxtons.co.uk', '/homes?view=details', '93.184.216.34', 10)
        pinned.assert_called_once_with('www.foxtons.co.uk', '93.184.216.34', 10)
        transport.connect.assert_called_once_with()
        transport.request.assert_called_once()
        self.assertEqual(('GET', '/homes?view=details'), transport.request.call_args.args)
        headers = {key.lower(): value for key, value in
                   transport.request.call_args.kwargs['headers'].items()}
        self.assertEqual({'user-agent', 'accept', 'accept-encoding', 'connection'}, set(headers))
        self.assertEqual('identity', headers['accept-encoding'])
        self.assertNotIn('cookie', headers)
        self.assertNotIn('authorization', headers)
        self.assertNotIn('proxy-authorization', headers)
        transport.getresponse.assert_called_once_with()
        self.assertIs(returned, transport)
        self.assertIs(response, transport.getresponse.return_value)


if __name__ == '__main__':
    unittest.main()
