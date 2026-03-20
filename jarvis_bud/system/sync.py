"""Optional local-network multi-device sync via zeroconf."""

from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional


@dataclass
class SyncPeer:
    name: str
    host: str
    port: int
    status: Dict[str, object]


class MultiDeviceSync:
    """Advertise and consume simple target/report state over LAN."""

    def __init__(
        self,
        get_state: Callable[[], Dict[str, object]],
        add_target: Callable[[str], None],
        reports_dir: str = "reports",
        port: int = 8091,
        service_type: str = "_omnibot._tcp.local.",
    ):
        self.get_state = get_state
        self.add_target = add_target
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.port = port
        self.service_type = service_type
        self._http_server: Optional[ThreadingHTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None
        self._zc = None
        self._service_info = None
        self._enabled = False

    def _build_handler(self):
        parent = self

        class SyncHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args):  # noqa: A003
                return

            def _send_json(self, payload: Dict[str, object], status: int = 200):
                body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802
                if self.path == "/status":
                    payload = parent.get_state()
                    self._send_json(payload)
                    return
                if self.path.startswith("/reports/"):
                    filename = self.path.split("/reports/", 1)[1]
                    report_path = (parent.reports_dir / filename).resolve()
                    if not report_path.exists() or parent.reports_dir.resolve() not in report_path.parents:
                        self.send_response(404)
                        self.end_headers()
                        return
                    data = report_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self):  # noqa: N802
                if self.path != "/targets":
                    self.send_response(404)
                    self.end_headers()
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length)
                    payload = json.loads(raw.decode("utf-8") or "{}")
                    target = str(payload.get("target", "")).strip()
                    if not target:
                        self._send_json({"ok": False, "error": "missing target"}, status=400)
                        return
                    parent.add_target(target)
                    self._send_json({"ok": True, "target": target}, status=200)
                except Exception as exc:
                    self._send_json({"ok": False, "error": str(exc)}, status=500)

        return SyncHandler

    def _local_ip(self) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self) -> bool:
        try:
            handler = self._build_handler()
            self._http_server = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
            self._http_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
            self._http_thread.start()
        except Exception:
            self._http_server = None
            self._http_thread = None
            return False

        try:
            from zeroconf import IPVersion, ServiceInfo, Zeroconf  # type: ignore

            hostname = socket.gethostname()
            ip = socket.inet_aton(self._local_ip())
            self._zc = Zeroconf(ip_version=IPVersion.V4Only)
            self._service_info = ServiceInfo(
                type_=self.service_type,
                name=f"{hostname}.{self.service_type}",
                addresses=[ip],
                port=self.port,
                properties={b"device": hostname.encode("utf-8")},
                server=f"{hostname}.local.",
            )
            self._zc.register_service(self._service_info)
            self._enabled = True
            return True
        except Exception:
            self._enabled = True
            return True

    def stop(self) -> None:
        if self._http_server:
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None
        if self._zc and self._service_info:
            try:
                self._zc.unregister_service(self._service_info)
            except Exception:
                pass
        if self._zc:
            try:
                self._zc.close()
            except Exception:
                pass
        self._zc = None
        self._service_info = None
        self._enabled = False

    def discover_peers(self, timeout_s: float = 1.5) -> List[SyncPeer]:
        peers: List[SyncPeer] = []
        try:
            from zeroconf import ServiceBrowser, ServiceListener, Zeroconf  # type: ignore

            class _Listener(ServiceListener):
                def __init__(self):
                    self.names: List[str] = []

                def add_service(self, zc, type_, name):  # noqa: N803
                    self.names.append(name)

                def update_service(self, zc, type_, name):  # noqa: N803
                    if name not in self.names:
                        self.names.append(name)

                def remove_service(self, zc, type_, name):  # noqa: N803
                    return

            zc = Zeroconf()
            listener = _Listener()
            browser = ServiceBrowser(zc, self.service_type, listener)
            browser.join(timeout_s)
            for name in listener.names:
                info = zc.get_service_info(self.service_type, name, int(timeout_s * 1000))
                if info is None or not info.addresses:
                    continue
                host = socket.inet_ntoa(info.addresses[0])
                port = info.port
                if host in {"127.0.0.1", "0.0.0.0"} and port == self.port:
                    continue
                status = {}
                try:
                    with urllib.request.urlopen(f"http://{host}:{port}/status", timeout=1.2) as response:
                        status = json.loads(response.read().decode("utf-8"))
                except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
                    status = {}
                peers.append(SyncPeer(name=name, host=host, port=port, status=status))
            zc.close()
        except Exception:
            return peers
        return peers

    def push_target(self, host: str, port: int, target: str) -> bool:
        payload = json.dumps({"target": target}, ensure_ascii=True).encode("utf-8")
        req = urllib.request.Request(
            f"http://{host}:{port}/targets",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=1.2) as response:
                return 200 <= response.status < 300
        except urllib.error.URLError:
            return False
