"""
Healthcare Pipeline — KNIME Windows Bridge
============================================
Lightweight HTTP server that runs on the Windows host to execute
KNIME batch workflows. The Flask API container calls this bridge
via host.docker.internal instead of trying to invoke KNIME from
inside the Linux container.

Usage:
    python knime_bridge.py

Or double-click run_knime_bridge.bat to start on port 9999.
"""

import json
import os
import subprocess
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = os.environ.get("BRIDGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("BRIDGE_PORT", "9999"))

KNIME_EXE = os.environ.get(
    "KNIME_EXECUTABLE",
    r"C:\Program Files\KNIME\knime.exe",
)
WORKFLOW_DIR = os.environ.get(
    "KNIME_WORKFLOW_PATH",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "knime_workflow",
        "health_cleaning.knwf",
    ),
)


class KnimeHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        start = time.time()
        try:
            result = subprocess.run(
                [
                    KNIME_EXE,
                    "-nosplash",
                    "-application",
                    "org.knime.product.KNIME_BATCH_APPLICATION",
                    "-workflowDir",
                    WORKFLOW_DIR,
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            body = json.dumps({
                "status": "completed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
                "execution_time_seconds": round(time.time() - start, 2),
                "message": "Real KNIME execution via Windows bridge",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            self.send_response(200)
        except subprocess.TimeoutExpired:
            body = json.dumps({
                "status": "timeout",
                "error": "KNIME execution timed out (600s)",
                "execution_time_seconds": round(time.time() - start, 2),
            })
            self.send_response(504)
        except FileNotFoundError:
            body = json.dumps({
                "status": "failed",
                "error": f"KNIME executable not found: {KNIME_EXE}",
            })
            self.send_response(500)
        except Exception as e:
            body = json.dumps({
                "status": "failed",
                "error": str(e),
                "execution_time_seconds": round(time.time() - start, 2),
            })
            self.send_response(500)

        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write(f"[KNIME Bridge] {args[0]} {args[1]} {args[2]}\n")


if __name__ == "__main__":
    print(f"KNIME bridge listening on {HOST}:{PORT}")
    print(f"  KNIME:   {KNIME_EXE}")
    print(f"  Workflow: {WORKFLOW_DIR}")
    print("Waiting for requests from Flask API...")
    HTTPServer((HOST, PORT), KnimeHandler).serve_forever()
