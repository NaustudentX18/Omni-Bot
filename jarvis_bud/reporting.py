"""HTML reporting and encrypted USB export pipeline."""

from __future__ import annotations

import html
import json
import os
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


MITRE_MAP = {
    "network_recon": ("TA0043", "Reconnaissance"),
    "wifi_crack.capture": ("T1040", "Network Sniffing"),
    "wifi_crack.deauth": ("T1498", "Network Denial of Service"),
    "sqlmap": ("T1190", "Exploit Public-Facing Application"),
    "hydra": ("T1110", "Brute Force"),
    "arp_spoof": ("T1557", "Adversary-in-the-Middle"),
}


@dataclass
class TimelineEvent:
    ts: float
    event: str
    detail: str
    severity: int


class ReportBuilder:
    def __init__(self, vibe_level: str = "cinematic"):
        self.vibe_level = vibe_level
        self.events: List[TimelineEvent] = []

    def ingest_audit_jsonl(self, path: str) -> None:
        ledger = Path(path)
        if not ledger.exists():
            return
        with ledger.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                evt = obj.get("event", "unknown")
                payload = obj.get("payload", {})
                detail = json.dumps(payload, ensure_ascii=True)[:280]
                severity = int(payload.get("risk", 1)) if isinstance(payload, dict) else 1
                self.events.append(TimelineEvent(ts=float(obj.get("ts", time.time())), event=evt, detail=detail, severity=severity))

    @staticmethod
    def _sev_color(severity: int) -> str:
        if severity >= 8:
            return "#ff4d4d"
        if severity >= 6:
            return "#ffae42"
        if severity >= 4:
            return "#00d4ff"
        return "#60ff9f"

    def to_html(self) -> str:
        rows = []
        for item in sorted(self.events, key=lambda e: e.ts):
            mitre = MITRE_MAP.get(item.event, ("-", "Unmapped"))
            color = self._sev_color(item.severity)
            event = html.escape(item.event, quote=True)
            detail = html.escape(item.detail, quote=True)
            mitre_label = f"{html.escape(str(mitre[0]), quote=True)} / {html.escape(str(mitre[1]), quote=True)}"
            rows.append(
                f"<tr>"
                f"<td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item.ts))}</td>"
                f"<td>{event}</td>"
                f"<td>{mitre_label}</td>"
                f"<td style='color:{color};font-weight:bold'>{item.severity}</td>"
                f"<td>{detail}</td>"
                f"</tr>"
            )

        neon_bg = "#0b0f1f" if self.vibe_level != "stealth" else "#111111"
        accent = "#00f7ff" if self.vibe_level == "cinematic" else "#5bff8d"
        return f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>NXTGENAI Deployment Report</title>
<style>
body {{ background:{neon_bg}; color:#d7e6ff; font-family: ui-monospace, monospace; }}
h1 {{ color:{accent}; text-shadow: 0 0 12px {accent}; }}
table {{ width:100%; border-collapse: collapse; }}
th, td {{ border:1px solid #29324a; padding:8px; vertical-align: top; }}
th {{ background:#1a2440; color:#8bc4ff; }}
.timeline {{ margin-top: 20px; }}
</style></head>
<body>
<h1>NXTGENAI // OPERATION TIMELINE</h1>
<p>Single-file report with severity mapping and MITRE ATT&amp;CK tagging.</p>
<table class="timeline">
<thead><tr><th>Timestamp</th><th>Event</th><th>MITRE ATT&CK</th><th>Severity</th><th>Detail</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body></html>"""

    def write_html(self, path: str = "reports/nxtgenai_report.html") -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_html(), encoding="utf-8")
        return str(target)


def _find_usb_mount() -> Optional[Path]:
    candidates = [Path("/media"), Path("/mnt"), Path("/run/media")]
    for base in candidates:
        if not base.exists():
            continue
        for child in base.iterdir():
            if child.is_dir() and os.access(child, os.W_OK):
                return child
    return None


def export_encrypted_zip(
    source_file: str,
    password: str,
    target_filename: str = "nxtgenai_export.zip",
) -> Optional[str]:
    mount = _find_usb_mount()
    if not mount:
        return None
    destination = mount / target_filename
    source = Path(source_file)
    if not source.exists():
        return None

    try:
        import pyzipper  # type: ignore

        with pyzipper.AESZipFile(
            destination,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(password.encode("utf-8"))
            zf.writestr(source.name, source.read_bytes())
        return str(destination)
    except Exception:
        # Fallback is intentionally explicit in filename so operators can detect non-AES export.
        fallback = destination.with_name(destination.stem + "_NO_AES.zip")
        with zipfile.ZipFile(fallback, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(source, arcname=source.name)
        return str(fallback)
