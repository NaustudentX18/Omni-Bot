"""Offline tool runner with safety rails, validation, and emergency controls."""

from __future__ import annotations

import grp
import os
import pwd
import re
import shlex
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jarvis_bud.audit import AuditLogger

_IPV4_RE = re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$")
_CIDR_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)/(?:[0-9]|[12]\d|3[0-2])$"
)
_URL_RE = re.compile(r"^https?://[a-zA-Z0-9.\-]+(?::\d+)?(?:/[^\s]*)?$")
_IFACE_RE = re.compile(r"^[a-zA-Z0-9_.:-]{1,32}$")
_SAFE_PATH_RE = re.compile(r"^[a-zA-Z0-9_./-]{1,240}$")
_MAC_RE = re.compile(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$")


@dataclass
class ToolResult:
    ok: bool
    tool: str
    command: str
    stdout: str
    stderr: str
    returncode: int
    risk: int
    duration_s: float
    skipped: bool = False
    dry_run: bool = False


class ToolRunner:
    """Safety-hardened subprocess tool runner for Pi-native operations."""

    def __init__(
        self,
        audit: AuditLogger,
        dry_run: bool = True,
        risk_confirm_threshold: int = 6,
        confirm_callback: Callable[[str, int], bool] | None = None,
        drop_privileges: bool = True,
    ):
        self.audit = audit
        self.dry_run = dry_run
        self.risk_confirm_threshold = risk_confirm_threshold
        self.confirm_callback = confirm_callback
        self.drop_privileges = drop_privileges
        self._tracked: dict[int, subprocess.Popen] = {}

    # ---- Validators -----------------------------------------------------
    def _validate_ip(self, value: str) -> bool:
        return bool(_IPV4_RE.fullmatch(value))

    def _validate_cidr(self, value: str) -> bool:
        return bool(_CIDR_RE.fullmatch(value))

    def _validate_url(self, value: str) -> bool:
        if not _URL_RE.fullmatch(value):
            return False
        parts = urlparse(value)
        return parts.scheme in {"http", "https"} and bool(parts.netloc)

    def _validate_iface(self, value: str) -> bool:
        return bool(_IFACE_RE.fullmatch(value))

    def _validate_path(self, value: str) -> bool:
        if not _SAFE_PATH_RE.fullmatch(value):
            return False
        return ".." not in Path(value).parts

    def _validate_mac(self, value: str) -> bool:
        return bool(_MAC_RE.fullmatch(value))

    # ---- Process control ------------------------------------------------
    def _drop_privileges_factory(self) -> Callable[[], None]:
        def _drop() -> None:
            if os.geteuid() != 0:
                return
            try:
                nobody = pwd.getpwnam("nobody")
                nogroup = grp.getgrnam("nogroup")
                os.setgid(nogroup.gr_gid)
                os.setuid(nobody.pw_uid)
            except (KeyError, PermissionError):
                # Safety-first fallback: if privilege drop fails, continue with current uid.
                return

        return _drop

    def stop_all(self, reason: str = "emergency-stop") -> dict[str, Any]:
        """Terminate every tracked subprocess group."""
        stopped: list[int] = []
        for pid, proc in list(self._tracked.items()):
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGTERM)
                stopped.append(pid)
            except ProcessLookupError:
                pass
            except Exception:
                try:
                    proc.terminate()
                    stopped.append(pid)
                except Exception:
                    pass

        # Escalate to hard kill for stragglers.
        time.sleep(0.2)
        for pid, proc in list(self._tracked.items()):
            if proc.poll() is None:
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        self._tracked = {pid: p for pid, p in self._tracked.items() if p.poll() is None}
        self.audit.log_event("tool.stop_all", {"reason": reason, "stopped_pids": stopped})
        return {"stopped_pids": stopped, "active_after_stop": list(self._tracked)}

    # ---- Generic execution ---------------------------------------------
    def _confirm_if_needed(self, tool: str, risk: int) -> bool:
        if risk < self.risk_confirm_threshold:
            return True
        if not self.confirm_callback:
            return False
        return bool(self.confirm_callback(tool, risk))

    def _exec(self, tool: str, cmd: list[str], risk: int, timeout: int = 120) -> ToolResult:
        cmd_str = " ".join(shlex.quote(part) for part in cmd)
        self.audit.log_event(
            "tool.call", {"tool": tool, "command": cmd_str, "risk": risk, "dry_run": self.dry_run}
        )

        if not self._confirm_if_needed(tool, risk):
            self.audit.log_event(
                "tool.blocked", {"tool": tool, "reason": "confirmation-denied", "risk": risk}
            )
            return ToolResult(
                ok=False,
                tool=tool,
                command=cmd_str,
                stdout="",
                stderr="blocked: explicit confirmation required",
                returncode=1,
                risk=risk,
                duration_s=0.0,
                skipped=True,
            )

        if self.dry_run:
            self.audit.log_event("tool.dry_run", {"tool": tool, "command": cmd_str, "risk": risk})
            return ToolResult(
                ok=True,
                tool=tool,
                command=cmd_str,
                stdout="dry-run: command not executed",
                stderr="",
                returncode=0,
                risk=risk,
                duration_s=0.0,
                dry_run=True,
            )

        start = time.monotonic()
        preexec = self._drop_privileges_factory() if self.drop_privileges else None
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
                preexec_fn=preexec,
            )
        except FileNotFoundError:
            self.audit.log_event("tool.missing_binary", {"tool": tool, "command": cmd_str})
            return ToolResult(
                ok=False,
                tool=tool,
                command=cmd_str,
                stdout="",
                stderr="binary not found",
                returncode=127,
                risk=risk,
                duration_s=0.0,
            )
        self._tracked[proc.pid] = proc
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            code = proc.returncode or 0
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()
            stdout, stderr = proc.communicate()
            code = 124
        finally:
            self._tracked.pop(proc.pid, None)

        duration = time.monotonic() - start
        self.audit.log_event(
            "tool.result",
            {
                "tool": tool,
                "returncode": code,
                "duration_s": round(duration, 3),
                "stdout_preview": (stdout or "")[:180],
                "stderr_preview": (stderr or "")[:180],
            },
        )
        return ToolResult(
            ok=code == 0,
            tool=tool,
            command=cmd_str,
            stdout=stdout or "",
            stderr=stderr or "",
            returncode=code,
            risk=risk,
            duration_s=duration,
        )

    # ---- Tool wrappers --------------------------------------------------
    def network_recon(self, target_cidr: str) -> ToolResult:
        if not self._validate_cidr(target_cidr):
            raise ValueError("Invalid CIDR target")
        return self._exec("network_recon", ["nmap", "-sn", target_cidr], risk=3, timeout=180)

    def web_pentest(self, target_url: str) -> ToolResult:
        if not self._validate_url(target_url):
            raise ValueError("Invalid URL target")
        return self._exec(
            "web_pentest", ["nmap", "-sV", "--script", "http-enum", target_url], risk=5, timeout=240
        )

    def arp_spoof(self, iface: str, target_ip: str, gateway_ip: str) -> ToolResult:
        if not self._validate_iface(iface):
            raise ValueError("Invalid interface")
        if not self._validate_ip(target_ip) or not self._validate_ip(gateway_ip):
            raise ValueError("Invalid IP target")
        return self._exec(
            "arp_spoof", ["arpspoof", "-i", iface, "-t", target_ip, gateway_ip], risk=8, timeout=120
        )

    def hydra(self, target_ip: str, service: str, user_list: str, pass_list: str) -> ToolResult:
        if not self._validate_ip(target_ip):
            raise ValueError("Invalid IP target")
        if service not in {"ssh", "ftp", "http-get", "rdp"}:
            raise ValueError("Unsupported service")
        if not self._validate_path(user_list) or not self._validate_path(pass_list):
            raise ValueError("Invalid wordlist path")
        return self._exec(
            "hydra",
            ["hydra", "-L", user_list, "-P", pass_list, f"{target_ip}", service],
            risk=9,
            timeout=600,
        )

    def sqlmap(self, target_url: str) -> ToolResult:
        if not self._validate_url(target_url):
            raise ValueError("Invalid URL target")
        return self._exec("sqlmap", ["sqlmap", "-u", target_url, "--batch"], risk=7, timeout=900)

    def wifi_crack(
        self,
        iface: str,
        capture_prefix: str = "/tmp/wifi_capture",
        bssid: str | None = None,
        channel_list: str = "1,6,11",
        deauth_count: int = 10,
    ) -> dict[str, ToolResult]:
        """Capture WPA handshakes with channel hop + optional targeted deauth.

        Output conversion attempts hashcat-ready .22000 through hcxpcapngtool.
        """
        if not self._validate_iface(iface):
            raise ValueError("Invalid interface")
        if not self._validate_path(capture_prefix):
            raise ValueError("Invalid capture path")
        if bssid and not self._validate_mac(bssid):
            raise ValueError("Invalid BSSID")

        results: dict[str, ToolResult] = {}
        results["capture"] = self._exec(
            "wifi_crack.capture",
            [
                "airodump-ng",
                "--band",
                "bg",
                "--channel",
                channel_list,
                "--write",
                capture_prefix,
                "--output-format",
                "pcap",
                iface,
            ],
            risk=6,
            timeout=180,
        )

        if bssid:
            results["deauth"] = self._exec(
                "wifi_crack.deauth",
                ["aireplay-ng", "--deauth", str(deauth_count), "-a", bssid, iface],
                risk=8,
                timeout=120,
            )

        pcap_file = f"{capture_prefix}-01.pcap"
        h22000 = f"{capture_prefix}.22000"
        results["convert"] = self._exec(
            "wifi_crack.convert",
            ["hcxpcapngtool", "-o", h22000, pcap_file],
            risk=4,
            timeout=120,
        )
        return results

    def suggest_wordlists(self, recon_text: str) -> list[str]:
        suggestions = []
        lower = recon_text.lower()
        if any(token in lower for token in ("wordpress", "wp-content", "wp-admin")):
            suggestions.append("/usr/share/seclists/Discovery/Web-Content/CMS/wordpress.fuzz.txt")
        if any(token in lower for token in ("login", "auth", "signin")):
            suggestions.append(
                "/usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt"
            )
        if any(token in lower for token in ("api", "graphql", "swagger")):
            suggestions.append(
                "/usr/share/seclists/Discovery/Web-Content/api/api-endpoints-res.txt"
            )
        if not suggestions:
            suggestions.append("/usr/share/seclists/Discovery/Web-Content/common.txt")
        return suggestions

    def feroxbuster(self, target_url: str, wordlist: str | None = None) -> ToolResult:
        if not self._validate_url(target_url):
            raise ValueError("Invalid URL target")
        cmd = ["feroxbuster", "-u", target_url]
        if wordlist and self._validate_path(wordlist):
            cmd.extend(["-w", wordlist])
        return self._exec("feroxbuster", cmd, risk=5, timeout=300)

    def nikto(self, target_url: str) -> ToolResult:
        if not self._validate_url(target_url):
            raise ValueError("Invalid URL target")
        return self._exec("nikto", ["nikto", "-h", target_url], risk=5, timeout=420)

    def gobuster(self, target_url: str, wordlist: str) -> ToolResult:
        if not self._validate_url(target_url):
            raise ValueError("Invalid URL target")
        if not self._validate_path(wordlist):
            raise ValueError("Invalid wordlist path")
        return self._exec(
            "gobuster", ["gobuster", "dir", "-u", target_url, "-w", wordlist], risk=5, timeout=420
        )

    def dnsrecon(self, domain: str) -> ToolResult:
        if not re.fullmatch(r"[a-zA-Z0-9.-]{1,253}", domain):
            raise ValueError("Invalid domain")
        return self._exec("dnsrecon", ["dnsrecon", "-d", domain], risk=3, timeout=240)

    def theharvester(self, domain: str) -> ToolResult:
        if not re.fullmatch(r"[a-zA-Z0-9.-]{1,253}", domain):
            raise ValueError("Invalid domain")
        return self._exec(
            "theHarvester", ["theHarvester", "-d", domain, "-b", "bing"], risk=3, timeout=240
        )
