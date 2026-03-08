"""
OrthoBraceForge — OctoMCP Agent
Wraps OctoEverywhere/mcp (Printer state/control broker).
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from config import EXPORT_DIR, OCTOPRINT_API_KEY, OCTOPRINT_CONNECT_TIMEOUT_SEC, OCTOPRINT_URL

from .base import AgentResult, BaseAgent

logger = logging.getLogger("orthobraceforge.agents")


class OctoMCPAgent(BaseAgent):
    """
    Local MCP broker for 3D printer communication.
    Interfaces with OctoPrint/Klipper via local network.
    """

    def __init__(self):
        super().__init__("octo_mcp")
        self._printer_url = os.environ.get("OCTOPRINT_URL", OCTOPRINT_URL)
        self._api_key = os.environ.get("OCTOPRINT_API_KEY", OCTOPRINT_API_KEY)
        if not self._api_key:
            try:
                import keyring
                self._api_key = keyring.get_password("orthobraceforge", "octoprint_api_key") or ""
            except ImportError:
                pass

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        action = params.get("action", "status")
        self._log(f"MCP action: {action}")

        if action == "status":
            status = self._get_printer_status()
            return AgentResult(
                success=True, agent_name=self.name,
                output_data={"printer_status": status},
                trace_log=list(self._trace),
            )
        elif action == "upload":
            gcode_path = params.get("gcode_path", "")
            result = self._upload_gcode(gcode_path)
            return AgentResult(
                success=result, agent_name=self.name,
                output_data={"uploaded": result},
                trace_log=list(self._trace),
            )
        elif action == "start_print":
            result = self._start_print(params.get("filename", ""))
            return AgentResult(
                success=result, agent_name=self.name,
                output_data={"print_started": result},
                trace_log=list(self._trace),
            )
        elif action == "pause":
            return AgentResult(
                success=True, agent_name=self.name,
                output_data={"paused": True},
                trace_log=list(self._trace),
            )
        else:
            return AgentResult(
                success=False, agent_name=self.name,
                errors=[f"Unknown action: {action}"],
                trace_log=list(self._trace),
            )

    def _validate_api_key(self) -> None:
        """Raise ValueError if API key is not configured."""
        if not self._api_key:
            raise ValueError(
                "OctoPrint API key is not configured. "
                "Set the OCTOPRINT_API_KEY environment variable."
            )

    def _get_printer_status(self) -> Dict:
        """Query printer status via OctoPrint API."""
        try:
            self._validate_api_key()
            import urllib.request
            req = urllib.request.Request(
                f"{self._printer_url}/api/printer",
                headers={"X-Api-Key": self._api_key},
            )
            with urllib.request.urlopen(req, timeout=OCTOPRINT_CONNECT_TIMEOUT_SEC) as resp:
                return json.loads(resp.read())
        except ValueError as e:
            self._log(f"Printer config error: {e}")
            return {"state": "unconfigured", "error": str(e)}
        except (OSError, TimeoutError) as e:
            self._log(f"Printer status error: {e}")
            return {"state": "offline", "error": str(e)}

    def _upload_gcode(self, gcode_path: str) -> bool:
        """Upload G-code file to OctoPrint via multipart POST /api/files/local."""
        import urllib.error
        import urllib.request

        self._validate_api_key()

        gcode_file = Path(gcode_path).resolve()
        # Path must exist and must be inside EXPORT_DIR (allowlist check)
        try:
            gcode_file.relative_to(EXPORT_DIR.resolve())
        except ValueError:
            logger.warning(f"[{self.name}] Security: gcode_path outside EXPORT_DIR: {gcode_path}")
            self._log(f"Security: gcode_path outside EXPORT_DIR: {gcode_path}")
            return False

        if not gcode_file.exists():
            self._log(f"G-code file not found: {gcode_file}")
            return False

        self._log(f"Uploading {gcode_file.name} to OctoPrint …")
        boundary = "----OBFBoundary"
        filename = gcode_file.name
        file_data = gcode_file.read_bytes()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"{self._printer_url}/api/files/local",
            data=body,
            headers={
                "X-Api-Key": self._api_key,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=OCTOPRINT_CONNECT_TIMEOUT_SEC) as resp:
                resp_data = json.loads(resp.read())
                self._log(f"Upload success: {resp_data.get('name', filename)}")
                return True
        except urllib.error.HTTPError as e:
            self._log(f"Upload HTTP error {e.code}: {e.reason}")
            return False
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            self._log(f"Upload error: {e}")
            return False

    def _start_print(self, filename: str) -> bool:
        """Issue a start-job command to OctoPrint via POST /api/job."""
        import urllib.error
        import urllib.request

        self._validate_api_key()

        if not filename:
            self._log("start_print: filename must not be empty")
            return False

        self._log(f"Sending print-start command for: {filename}")
        payload = json.dumps({"command": "start"}).encode()
        req = urllib.request.Request(
            f"{self._printer_url}/api/job",
            data=payload,
            headers={
                "X-Api-Key": self._api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=OCTOPRINT_CONNECT_TIMEOUT_SEC) as resp:
                self._log(f"Print started — HTTP {resp.status}")
                return resp.status == 204
        except urllib.error.HTTPError as e:
            self._log(f"Print-start HTTP error {e.code}: {e.reason}")
            return False
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            self._log(f"Print-start error: {e}")
            return False
