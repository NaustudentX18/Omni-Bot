"""Main entry point with deployment-grade safety, audit, and offline UX."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import random
import sys
import time
from typing import Optional

from jarvis_bud.ai import EdgeBrain
from jarvis_bud.audit import AuditLogger
from jarvis_bud.config import ConfigManager
from jarvis_bud.core import BudManager, LocalOllamaClient
from jarvis_bud.dashboard import DashboardServer
from jarvis_bud.hardware import Battery, SpeechSynth, SpeechToTextEngine, WhisplayIO
from jarvis_bud.plugins import PluginLoader
from jarvis_bud.reporting import ReportBuilder, export_encrypted_zip
from jarvis_bud.system import MultiDeviceSync, OTAUpdater
from jarvis_bud.tools import ToolRunner
from jarvis_bud.ui import FrameRenderer, WaveformAnimator
from jarvis_bud.voice import VoiceCommandParser, VoiceIntent
from jarvis_bud.wizard import SetupWizard
from ui import button_confirm, emergency_banner_text


class JarvisBud:
    """Main Jarvis-Bud/NXTGENAI deployment controller."""

    def __init__(
        self,
        config_path: str = "config/config.json",
        buds_path: str = "jarvis_bud/buds.json",
        audit_path: str = "logs/audit_chain.jsonl",
    ):
        self.config_manager = ConfigManager(config_path)
        self.buds_path = buds_path
        self.audit = AuditLogger(audit_path)
        self.audit.log_event(
            "boot",
            {
                "config_path": config_path,
                "audit_chain_ok": self.audit.verify_chain(),
                "pid": os.getpid(),
            },
        )

        # Hardware
        self.whisplay: Optional[WhisplayIO] = None
        self.battery: Optional[Battery] = None
        tts_model = self.config_manager.get("tts.model_path", "models/piper/en_US-lessac-medium.onnx")
        tts_profile = self.config_manager.get("tts.profile", "cyberpunk")
        self.tts = SpeechSynth(piper_model=tts_model, profile=tts_profile)
        stt_model = self.config_manager.get("stt.model_size", "tiny.en")
        stt_sample_rate = int(self.config_manager.get("stt.sample_rate", 16000))
        self.stt = SpeechToTextEngine(model_size=stt_model, sample_rate=stt_sample_rate)

        # UI
        self.renderer: Optional[FrameRenderer] = None
        self.animator = WaveformAnimator()
        self.dashboard: Optional[DashboardServer] = None
        self.ota_updater = OTAUpdater(repo_path=".")
        self.sync_service: Optional[MultiDeviceSync] = None
        self._last_sync_peer_count = 0

        # AI and personalities
        self.brain = EdgeBrain(audit=self.audit, vibe_level=self.config_manager.get_vibe_level())
        self.bud_manager: Optional[BudManager] = None
        self.voice_parser = VoiceCommandParser()

        # Tool runner with risk-gated execution
        self.tools = ToolRunner(
            audit=self.audit,
            dry_run=self.config_manager.is_dry_run(),
            risk_confirm_threshold=6,
            confirm_callback=self._confirm_high_risk_action,
        )
        self.plugins = PluginLoader(audit=self.audit, tool_runner=self.tools)

        # State
        self.is_listening = False
        self.is_running = True
        self.current_bud = "Fogo"
        self.connectivity_mode = "offline"
        self._last_prompt = ""
        self._last_ai_thought = "Boot sequence complete"
        self._last_risk = 1
        self._targets = []
        self._last_haiku_ts = 0.0
        self._haikus = [
            "Neon rain whispers / silicon ghosts map the night / buttons wake the storm",
            "Battery moon glows / packet tides crash on dark ports / zero-two dreams loud",
            "Cold copper heartbeat / matrix petals drift in RAM / legends boot at dawn",
        ]
        self.god_mode = self.config_manager.is_god_mode()
        self._battery_snapshot = {"percentage": 100, "charging": False}
        self._last_battery_refresh = 0.0
        self._battery_refresh_interval_s = 2.0

    def _refresh_battery_snapshot(self, force: bool = False) -> dict:
        """Refresh cached battery status with light rate limiting."""
        now = time.monotonic()
        should_refresh = force or (now - self._last_battery_refresh) >= self._battery_refresh_interval_s
        if should_refresh and self.battery:
            status = self.battery.get_status()
            self._battery_snapshot["percentage"] = int(status.get("percentage", 100))
            self._battery_snapshot["charging"] = bool(status.get("charging", False))
            self._last_battery_refresh = now
        return self._battery_snapshot

    def run_first_boot_if_needed(self) -> bool:
        if not self.config_manager.is_configured():
            # Start the dashboard immediately so the web wizard is reachable
            # before hardware is initialised (safe — dashboard only needs config_manager).
            self.initialize_dashboard()
            print("\n" + "━" * 60)
            print("  FIRST-BOOT SETUP".center(60))
            print("━" * 60)
            print("\n  🌐  Web wizard (recommended):")
            print("       http://localhost:8080/setup")
            print("       http://<your-Pi-IP>:8080/setup\n")
            print("  Open that URL in any browser on the same network,")
            print("  or continue below for the terminal wizard.\n")
            print("━" * 60 + "\n")
            wizard = SetupWizard(config_path=self.config_manager.config_path, buds_path=self.buds_path)
            if wizard.run_interactive():
                self.config_manager.load()
                self.config_manager.load_runtime()
                return True
            print("\n❌ Setup wizard failed. Please try again.")
            return False
        return True

    def initialize_hardware(self) -> bool:
        print("\n🔧 Initializing hardware...\n")
        try:
            self.whisplay = WhisplayIO()
            if not self.whisplay.initialize():
                print("❌ Whisplay initialization failed")
                return False
            self.battery = Battery()
            self.battery.connect()
            self.whisplay.set_callbacks(
                on_button_a=self._on_button_a_pressed,
                on_button_b=self._on_button_b_pressed,
                on_button_b_long_press=self._on_button_b_long_pressed,
            )
            self.renderer = FrameRenderer()

            # Dramatic boot matrix animation for physical startup.
            if self.renderer and self.whisplay:
                for frame in range(20):
                    self.renderer.render_matrix_boot(self.whisplay.display, frame_idx=frame, total_frames=20)
                    time.sleep(0.03)
            print("✅ Hardware initialized successfully\n")
            return True
        except Exception as exc:
            print(f"❌ Hardware initialization error: {exc}")
            return False

    def initialize_ai(self) -> bool:
        print("\n🧠 Initializing offline-first AI stack...\n")
        try:
            configured_ollama = self.config_manager.get_ollama_url()
            candidates = ["127.0.0.1", "pironman", "naspi", "192.168.1.100", "192.168.1.101", "192.168.1.110"]
            if configured_ollama and configured_ollama.startswith("http://"):
                host = configured_ollama.replace("http://", "").split(":")[0]
                if host not in candidates:
                    candidates.insert(0, host)

            ollama = LocalOllamaClient(candidate_hosts=candidates, max_ping_ms=100.0)
            endpoint = ollama.scan()
            self.bud_manager = BudManager(
                ollama=ollama,
                openrouter_key=self.config_manager.get_openrouter_key(),
                brain=self.brain,
            )
            preferred = self.config_manager.get("bud.id", "fogo")
            self.bud_manager.set_active_bud(preferred if preferred in self.bud_manager.buds else "fogo")
            self.current_bud = self.bud_manager.active_profile.name

            if endpoint:
                self.connectivity_mode = "local"
                print(f"✅ Ollama endpoint: {endpoint.base_url} ({endpoint.latency_ms:.1f}ms)")
            elif self.bud_manager.openrouter and self.bud_manager.openrouter.is_available:
                self.connectivity_mode = "cloud"
                print("✅ Local offline, using OpenRouter failover")
            else:
                self.connectivity_mode = "offline"
                print("⚠️ No AI route available; fallback brain active")
            print()
            return True
        except Exception as exc:
            print(f"❌ AI initialization error: {exc}")
            self.connectivity_mode = "offline"
            return False

    def initialize_dashboard(self) -> bool:
        """Start local-only Flask dashboard for config and status."""
        if not self.config_manager.get("dashboard.enabled", True):
            return True
        self.dashboard = DashboardServer(app=self, host="127.0.0.1", port=8080)
        started = self.dashboard.start()
        if started:
            print("🌐 Dashboard ready at http://127.0.0.1:8080")
        else:
            print("⚠️ Dashboard failed to start")
        return started

    def initialize_sync(self) -> bool:
        if not self.config_manager.get("sync.enabled", False):
            return True
        self.sync_service = MultiDeviceSync(
            get_state=self.get_status_snapshot,
            add_target=self._add_target_from_sync,
            reports_dir="reports",
            port=int(self.config_manager.get("sync.port", 8091)),
        )
        started = self.sync_service.start()
        if started:
            print("🔁 Multi-device sync online")
        else:
            print("⚠️ Multi-device sync failed to start")
        return started

    def _add_target_from_sync(self, target: str) -> None:
        normalized = target.strip()
        if normalized and normalized not in self._targets:
            self._targets.append(normalized)
            self.audit.log_event("sync.target_received", {"target": normalized})

    def sync_with_peers(self) -> str:
        if not self.sync_service:
            return "Sync disabled."
        peers = self.sync_service.discover_peers()
        self._last_sync_peer_count = len(peers)
        merged = 0
        for peer in peers:
            targets = peer.status.get("targets", [])
            if not isinstance(targets, list):
                continue
            for target in targets:
                target_text = str(target).strip()
                if target_text and target_text not in self._targets:
                    self._targets.append(target_text)
                    merged += 1
        self.audit.log_event("sync.peer_scan", {"peer_count": len(peers), "merged_targets": merged})
        return f"Sync complete: {len(peers)} peer(s), {merged} new target(s)."

    def _confirm_ota_update(self, behind_count: int) -> bool:
        if os.environ.get("NXTGENAI_OTA_AUTO_APPLY", "").lower() in {"1", "true", "yes"}:
            return True
        if self.renderer and self.whisplay:
            self.renderer.render_message(
                self.whisplay.display,
                "OTA Update Ready",
                f"{behind_count} commit(s). Hold A to apply.",
                emoji="⬆️",
                message_type="warning",
            )
            self.whisplay.display.update()
            if button_confirm(self.whisplay.buttons, timeout_s=8.0):
                return True
        if sys.stdin.isatty():
            choice = input(f"Apply OTA update ({behind_count} commit(s)) now? [y/N]: ").strip().lower()
            return choice in {"y", "yes"}
        return False

    def check_and_apply_ota_on_boot(self) -> None:
        if not self.config_manager.get("ota.enabled", True):
            return
        status = self.ota_updater.check_updates()
        if status.error:
            self.audit.log_event("ota.check_error", {"error": status.error, "branch": status.branch})
            return
        if not status.available:
            return
        self.audit.log_event("ota.available", {"branch": status.branch, "behind_count": status.behind_count})
        if not self._confirm_ota_update(status.behind_count):
            self.audit.log_event("ota.skipped", {"branch": status.branch, "behind_count": status.behind_count})
            return
        ok, message = self.ota_updater.apply_update()
        self.audit.log_event("ota.apply", {"ok": ok, "message": message[:220], "branch": status.branch})
        if self.renderer and self.whisplay:
            self.renderer.render_message(
                self.whisplay.display,
                "OTA Update",
                "Applied. Reboot recommended." if ok else "Failed. Check logs.",
                emoji="✅" if ok else "❌",
                message_type="success" if ok else "error",
            )
            self.whisplay.display.update()
        self.tts.speak("Update applied. Please reboot soon." if ok else "Update failed.")

    def _on_button_a_pressed(self):
        print("🔘 Button A pressed (Listen)")
        if not self.is_listening and self.is_running:
            self.is_listening = True
            asyncio.create_task(self._listen_and_respond())

    def _on_button_b_pressed(self):
        print("🔘 Button B pressed (Cycle Bud)")
        if not self.bud_manager:
            return
        profile = self.bud_manager.cycle_bud()
        self.current_bud = profile.name
        self.config_manager.set("bud.id", profile.bud_id)
        self.config_manager.set("bud.name", profile.name)
        self.config_manager.set("bud.system_prompt", profile.system_prompt)
        self.config_manager.save()
        self.audit.log_event("bud.cycle", {"bud_id": profile.bud_id, "bud_name": profile.name})
        print(f"💫 Active Bud: {profile.name} {profile.emoji}")

    def _on_button_b_long_pressed(self):
        print("🛑 Button B long press detected")
        self.emergency_stop("button-b-long-press")

    def emergency_stop(self, reason: str):
        self.audit.log_event("emergency_stop", {"reason": reason})
        self.tools.stop_all(reason=reason)
        self.is_running = False
        self.is_listening = False
        if self.renderer and self.whisplay:
            self.renderer.render_message(
                self.whisplay.display,
                "EMERGENCY STOP",
                emergency_banner_text(reason),
                emoji="🛑",
                message_type="error",
            )
        self.tts.speak("Emergency stop engaged.")

    def _confirm_high_risk_action(self, tool_name: str, risk: int) -> bool:
        """Require explicit confirmation for risk >= threshold."""
        self.audit.log_event("confirm.request", {"tool": tool_name, "risk": risk})
        if os.environ.get("NXTGENAI_AUTO_CONFIRM", "").lower() in {"1", "true", "yes"}:
            self.audit.log_event("confirm.result", {"tool": tool_name, "risk": risk, "approved": True, "mode": "env"})
            return True

        if self.renderer and self.whisplay:
            self.renderer.render_message(
                self.whisplay.display,
                "HIGH RISK ACTION",
                f"{tool_name} risk {risk}/10",
                emoji="⚠️",
                message_type="warning",
            )
            self.renderer.render_risk_meter(self.whisplay.display, risk=risk, dry_run=self.tools.dry_run)
            self.whisplay.display.update()

        # Button-based confirmation path: hold Button A for a brief tap window.
        if self.whisplay and button_confirm(self.whisplay.buttons, timeout_s=6.0):
            self.audit.log_event(
                "confirm.result",
                {"tool": tool_name, "risk": risk, "approved": True, "mode": "button"},
            )
            return True

        if sys.stdin.isatty():
            choice = input(f"Confirm {tool_name} (risk {risk}/10)? [y/N]: ").strip().lower()
            approved = choice in {"y", "yes"}
            self.audit.log_event(
                "confirm.result",
                {"tool": tool_name, "risk": risk, "approved": approved, "mode": "stdin"},
            )
            return approved
        self.audit.log_event("confirm.result", {"tool": tool_name, "risk": risk, "approved": False, "mode": "timeout"})
        return False

    def _transcribe_audio(self, audio_data: bytes) -> str:
        """Offline STT path with tiny-model inference and deterministic fallback."""
        result = self.stt.transcribe(audio_data)
        self.audit.log_event(
            "voice.stt",
            {
                "backend": result.backend,
                "latency_ms": round(result.latency_ms, 2),
                "preview": result.text[:120],
            },
        )
        print(f"📝 STT backend={result.backend} latency={result.latency_ms:.1f}ms")
        return result.text

    def _execute_voice_intent(self, intent: VoiceIntent) -> str:
        self._last_risk = intent.risk
        self.audit.log_event("voice.command", {"command": intent.command, "args": intent.args, "risk": intent.risk})

        if intent.command == "status":
            battery = self._refresh_battery_snapshot(force=True)
            mode = "god-mode" if self.god_mode else "standard"
            return f"Status: battery {battery['percentage']}%, connectivity {self.connectivity_mode}, mode {mode}."

        if intent.command == "stop":
            self.emergency_stop("voice-stop")
            return "Emergency stop executed."

        if intent.command == "export":
            return self.export_reports() or "Export failed."

        if intent.command == "target_add":
            target = intent.args.get("target", "")
            if target:
                self._targets.append(target)
                if self.sync_service:
                    for peer in self.sync_service.discover_peers(timeout_s=0.5):
                        self.sync_service.push_target(peer.host, peer.port, target)
                return f"Target added: {target}"
            return "No target provided."

        if intent.command == "sync_now":
            return self.sync_with_peers()

        if intent.command == "god_mode":
            self.god_mode = True
            self.config_manager.set_runtime("god_mode", "true")
            return "God mode enabled: simulation speedrun engaged."

        if intent.command == "full_auto":
            if self.god_mode:
                return "Full-auto simulation complete: recon->analysis->report in cinematic mode."
            if not self._targets:
                return "No targets queued. Say 'target add X' first."
            target = self._targets[0].strip()
            target_cidr = target

            if "/" not in target:
                try:
                    parsed_ip = ipaddress.ip_address(target)
                except ValueError:
                    return (
                        f"Target '{target}' looks like a hostname. "
                        "Full-auto recon expects an IPv4 CIDR such as 192.168.1.0/24."
                    )

                if parsed_ip.version != 4:
                    return "Full-auto recon currently supports IPv4 CIDR targets only."

                target_cidr = f"{parsed_ip}/32"

            try:
                result = self.tools.network_recon(target_cidr)
            except ValueError:
                return (
                    f"Target '{target}' is not a valid IPv4 CIDR. "
                    "Use a target like 192.168.1.0/24."
                )
            if result:
                return f"Full-auto recon finished ({result.returncode})."
            return "Full-auto run skipped."

        if intent.command == "make_legendary":
            self.god_mode = True
            self.config_manager.set_runtime("god_mode", "true")
            self._last_ai_thought = "Legendary protocol online // neon overdrive"
            return "Legendary mode activated. Simulation blitz completed. Report aesthetics upgraded."

        if intent.command == "crack_wifi":
            if self.god_mode:
                return "God mode simulation: fake WPA handshake captured and converted to 22000 in 2.3s."
            iface = os.environ.get("NXTGENAI_WIFI_IFACE", "wlan0mon")
            results = self.tools.wifi_crack(iface=iface, capture_prefix="/tmp/nxtgenai_capture")
            return "WiFi workflow finished: " + ", ".join(f"{k}={v.returncode}" for k, v in results.items())

        # Default chat flow with planning/reflection under Bud manager.
        text = intent.args.get("text", "")
        plugin_reply = self.plugins.handle_voice_text(text=text, app=self)
        if plugin_reply:
            self._last_ai_thought = plugin_reply[:120]
            return plugin_reply
        self._last_prompt = text
        if self.bud_manager:
            return self.bud_manager.generate_response(text)
        return "AI manager unavailable."

    async def _listen_and_respond(self):
        if not self.whisplay:
            return
        try:
            if self.renderer:
                battery_snapshot = self._refresh_battery_snapshot(force=True)
                animation_frame = self.animator.get_frame("listening")
                self.renderer.render_status_hud(
                    self.whisplay.display,
                    bud_name=self.current_bud or "Jarvis-Bud",
                    battery_level=battery_snapshot["percentage"],
                    is_charging=battery_snapshot["charging"],
                    connectivity_status=self.connectivity_mode,
                    animation_frame=animation_frame,
                    activity_icon=self.bud_manager.active_icon(self._last_prompt) if self.bud_manager else "",
                )

            print("🎙️ Listening...")
            audio_data = await self.whisplay.capture_audio(seconds=4.0)
            if not audio_data:
                print("❌ No audio captured")
                self.is_listening = False
                return

            command_text = self._transcribe_audio(audio_data)
            intent = self.voice_parser.parse(command_text) or VoiceIntent(command="chat", args={"text": command_text}, risk=1)
            response = self._execute_voice_intent(intent)
            self._last_ai_thought = response[:120]
            if response:
                print(f"💬 Response: {response[:180]}")
                self.tts.speak(response[:220])
            self.is_listening = False
        except Exception as exc:
            print(f"❌ Error in listen/respond: {exc}")
            self.audit.log_event("voice.error", {"error": str(exc)})
            self.is_listening = False

    async def _update_display_loop(self):
        frame_interval = 1.0 / 60
        ticker_offset = 0
        while self.is_running:
            try:
                if self.whisplay and self.renderer:
                    if not self.is_listening and (time.monotonic() - self._last_haiku_ts) > 18:
                        self._last_ai_thought = random.choice(self._haikus)
                        self._last_haiku_ts = time.monotonic()
                    battery_snapshot = self._refresh_battery_snapshot()
                    if self.is_listening:
                        audio_level = self.whisplay.audio.get_audio_level() if self.whisplay else 0.5
                        animation_frame = self.animator.get_frame("listening", audio_level=audio_level)
                    else:
                        animation_frame = self.animator.get_frame("idle")

                    self.renderer.render_status_hud(
                        self.whisplay.display,
                        bud_name=self.current_bud or "Jarvis-Bud 🤖",
                        battery_level=battery_snapshot["percentage"],
                        is_charging=battery_snapshot["charging"],
                        connectivity_status=self.connectivity_mode,
                        animation_frame=animation_frame,
                        activity_icon=self.bud_manager.active_icon(self._last_prompt) if self.bud_manager else "",
                    )
                    self.renderer.render_ai_thought_ticker(self.whisplay.display, self._last_ai_thought, offset=ticker_offset)
                    self.renderer.render_risk_meter(self.whisplay.display, risk=self._last_risk, dry_run=self.tools.dry_run)
                    if not self.is_listening:
                        self.renderer.render_idle_matrix_overlay(self.whisplay.display, tick=ticker_offset)
                    if self.god_mode:
                        self.renderer.apply_glitch(self.whisplay.display, intensity=0.35)
                    self.whisplay.display.update()
                    ticker_offset += 1

                await asyncio.sleep(frame_interval)
            except Exception as exc:
                print(f"⚠️ Display update error: {exc}")
                await asyncio.sleep(frame_interval)

    async def _battery_monitor_loop(self):
        while self.is_running:
            try:
                if self.battery:
                    status = self._refresh_battery_snapshot(force=True)
                    if status["percentage"] < 10:
                        print("🚨 CRITICAL: Battery very low!")
                        self.audit.log_event("battery.critical", {"percentage": status["percentage"]})
                        if self.renderer and self.whisplay:
                            self.renderer.render_message(
                                self.whisplay.display,
                                "Battery Critical",
                                "Charge now or shutdown imminent.",
                                emoji="🪫",
                                message_type="error",
                            )
                await asyncio.sleep(10)
            except Exception as exc:
                print(f"⚠️ Battery monitor error: {exc}")
                await asyncio.sleep(10)

    async def async_main_loop(self):
        print("\n🚀 Starting Jarvis-Bud async event loop...\n")
        tasks = [asyncio.create_task(self._update_display_loop()), asyncio.create_task(self._battery_monitor_loop())]
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n\n⏹️ Shutting down...")
            self.is_running = False
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    def export_reports(self, passphrase: Optional[str] = None) -> Optional[str]:
        """Generate HTML report and export encrypted ZIP to mounted USB."""
        if self.renderer and self.whisplay:
            self.renderer.render_message(
                self.whisplay.display,
                "Export",
                "Building report timeline...",
                emoji="📦",
                message_type="info",
            )
            self.renderer.render_progress_overlay(self.whisplay.display, 0.25, label="Timeline")
            self.whisplay.display.update()

        builder = ReportBuilder(vibe_level=self.config_manager.get_vibe_level())
        builder.ingest_audit_jsonl(str(self.audit.path))
        html_path = builder.write_html("reports/nxtgenai_report.html")
        self.audit.log_event("report.generated", {"html_path": html_path})

        if self.renderer and self.whisplay:
            self.renderer.render_progress_overlay(self.whisplay.display, 0.7, label="Encrypt")
            self.whisplay.display.update()

        secret = passphrase or os.environ.get("NXTGENAI_EXPORT_PASS", "nxtgenai-2026")
        exported = export_encrypted_zip(source_file=html_path, password=secret)
        self.audit.log_event("report.export", {"html_path": html_path, "exported_path": exported})
        if self.renderer and self.whisplay:
            self.renderer.render_progress_overlay(self.whisplay.display, 1.0, label="Done")
            self.whisplay.display.update()
        return exported or html_path

    def get_status_snapshot(self) -> dict:
        battery = self._refresh_battery_snapshot(force=False)
        return {
            "is_running": self.is_running,
            "is_listening": self.is_listening,
            "current_bud": self.current_bud,
            "connectivity_mode": self.connectivity_mode,
            "god_mode": self.god_mode,
            "last_ai_thought": self._last_ai_thought,
            "targets": list(self._targets),
            "plugin_count": self.plugins.plugin_count,
            "sync_enabled": bool(self.sync_service),
            "sync_peers": self._last_sync_peer_count,
            "battery": {
                "percentage": battery.get("percentage", 100),
                "charging": battery.get("charging", False),
            },
        }

    def cleanup(self):
        print("\n🧹 Cleaning up...\n")
        try:
            self.tools.stop_all(reason="cleanup")
        except Exception:
            pass
        if self.dashboard:
            self.dashboard.stop()
        if self.sync_service:
            self.sync_service.stop()
        if self.whisplay:
            self.whisplay.cleanup()
        if self.battery:
            self.battery.disconnect()
        print("✅ Cleanup complete\n")

    def run(self):
        try:
            if not self.run_first_boot_if_needed():
                return False
            self.config_manager.print_config()
            self.current_bud = self.config_manager.get("bud.name", "Jarvis-Bud")
            if not self.initialize_hardware():
                print("❌ Critical hardware initialization failed")
                return False
            self.check_and_apply_ota_on_boot()
            self.initialize_ai()
            self.initialize_dashboard()
            self.initialize_sync()
            asyncio.run(self.async_main_loop())
            return True
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            return True
        except Exception as exc:
            print(f"\n❌ Fatal error: {exc}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            self.cleanup()


def main():
    """Entrypoint with export mode support."""
    if len(sys.argv) > 1 and sys.argv[1].lower() == "export":
        app = JarvisBud()
        exported = app.export_reports()
        print(exported or "export failed")
        app.cleanup()
        sys.exit(0 if exported else 1)

    app = JarvisBud()
    success = app.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
