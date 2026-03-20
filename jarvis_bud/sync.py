"""Multi-device sync over local network using Zeroconf (mDNS/DNS-SD).

Allows multiple Pi Zero 2 W nodes running NXTGENAI to discover each other,
share targets, and exchange reports—all without internet access.

Protocol:
  - Each node announces ``_nxtgenai._tcp.local.`` service via Zeroconf.
  - Peers connect over a simple HTTP API for data exchange.
  - All communication is LAN-only, no cloud required.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional


SERVICE_TYPE = "_nxtgenai._tcp.local."
DEFAULT_SYNC_PORT = 8081


@dataclass
class PeerNode:
    """A discovered peer on the local network."""

    name: str
    host: str
    port: int
    version: str = ""
    last_seen: float = 0.0
    targets: List[str] = field(default_factory=list)


class DeviceSync:
    """Manages mDNS service advertisement and peer discovery."""

    def __init__(
        self,
        node_name: Optional[str] = None,
        sync_port: int = DEFAULT_SYNC_PORT,
        version: str = "0.2.0",
    ):
        self.node_name = node_name or f"nxtgenai-{platform.node()}"
        self.sync_port = sync_port
        self.version = version
        self._peers: Dict[str, PeerNode] = {}
        self._shared_targets: List[str] = []
        self._shared_reports: List[str] = []
        self._zeroconf = None
        self._service_info = None
        self._browser = None
        self._http_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def peers(self) -> List[PeerNode]:
        with self._lock:
            cutoff = time.time() - 120
            return [p for p in self._peers.values() if p.last_seen > cutoff]

    def start(self) -> bool:
        """Start mDNS advertisement and peer discovery."""
        try:
            from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf  # type: ignore[import-untyped]
        except ImportError:
            print("⚠️  zeroconf not installed; multi-device sync disabled.")
            return False

        try:
            local_ip = self._get_local_ip()
            self._zeroconf = Zeroconf()
            self._service_info = ServiceInfo(
                SERVICE_TYPE,
                f"{self.node_name}.{SERVICE_TYPE}",
                addresses=[socket.inet_aton(local_ip)],
                port=self.sync_port,
                properties={
                    b"version": self.version.encode(),
                    b"node": self.node_name.encode(),
                },
            )
            self._zeroconf.register_service(self._service_info)

            self._browser = ServiceBrowser(self._zeroconf, SERVICE_TYPE, handlers=[self._on_service_state_change])

            self._start_sync_server()
            self._available = True
            print(f"📡 Sync service started: {self.node_name} on {local_ip}:{self.sync_port}")
            return True

        except Exception as exc:
            print(f"⚠️  Sync start failed: {exc}")
            return False

    def stop(self) -> None:
        """Unregister service and stop sync."""
        try:
            if self._zeroconf and self._service_info:
                self._zeroconf.unregister_service(self._service_info)
            if self._zeroconf:
                self._zeroconf.close()
        except Exception:
            pass
        self._available = False

    def share_targets(self, targets: List[str]) -> None:
        """Update shared targets list for peer access."""
        with self._lock:
            self._shared_targets = list(targets)

    def share_reports(self, report_paths: List[str]) -> None:
        """Update shared report paths for peer access."""
        with self._lock:
            self._shared_reports = list(report_paths)

    def fetch_peer_targets(self, peer_name: str) -> List[str]:
        """Fetch targets from a specific peer via HTTP."""
        peer = self._peers.get(peer_name)
        if not peer:
            return []
        try:
            import urllib.request
            url = f"http://{peer.host}:{peer.port}/sync/targets"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("targets", [])
        except Exception:
            return []

    def broadcast_target(self, target: str) -> int:
        """Share a target with all known peers. Returns count of peers notified."""
        count = 0
        for peer in self.peers:
            try:
                import urllib.request
                url = f"http://{peer.host}:{peer.port}/sync/targets"
                payload = json.dumps({"targets": [target]}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, method="POST")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=5):
                    count += 1
            except Exception:
                continue
        return count

    def _on_service_state_change(self, zeroconf, service_type, name, state_change):
        """Handle Zeroconf service state changes."""
        try:
            from zeroconf import ServiceStateChange  # type: ignore[import-untyped]
        except ImportError:
            return

        if state_change == ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info and info.addresses:
                host = socket.inet_ntoa(info.addresses[0])
                peer_name = info.properties.get(b"node", b"unknown").decode()
                if peer_name == self.node_name:
                    return
                with self._lock:
                    self._peers[peer_name] = PeerNode(
                        name=peer_name,
                        host=host,
                        port=info.port,
                        version=info.properties.get(b"version", b"?").decode(),
                        last_seen=time.time(),
                    )
                print(f"📡 Peer discovered: {peer_name} at {host}:{info.port}")

        elif state_change == ServiceStateChange.Removed:
            display_name = name.split(".")[0] if "." in name else name
            with self._lock:
                self._peers.pop(display_name, None)

    def _start_sync_server(self) -> None:
        """Start a minimal HTTP server for peer data exchange."""
        sync_self = self

        class SyncHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                if self.path == "/sync/targets":
                    with sync_self._lock:
                        data = {"targets": sync_self._shared_targets, "node": sync_self.node_name}
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode())

                elif self.path == "/sync/status":
                    data = {
                        "node": sync_self.node_name,
                        "version": sync_self.version,
                        "peers": len(sync_self.peers),
                        "targets": len(sync_self._shared_targets),
                    }
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode())

                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == "/sync/targets":
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length)
                    try:
                        data = json.loads(body.decode("utf-8"))
                        new_targets = data.get("targets", [])
                        with sync_self._lock:
                            for t in new_targets:
                                if t not in sync_self._shared_targets:
                                    sync_self._shared_targets.append(t)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"ok": True}).encode())
                    except Exception:
                        self.send_response(400)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

        server = HTTPServer(("0.0.0.0", self.sync_port), SyncHandler)
        self._http_thread = threading.Thread(target=server.serve_forever, name="sync-server", daemon=True)
        self._http_thread.start()

    @staticmethod
    def _get_local_ip() -> str:
        """Get the best local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
