"""
WorkAnalytics OS — Unified System Launcher (Task 2)
====================================================
Run this single script instead of opening two terminals:

    python start_app.py

What it does:
  1. Starts the Django development server in a child process.
  2. Waits for the server to be ready (polls port 8000).
  3. Starts the desktop tracking agent in a second child process.
  4. On Ctrl+C — gracefully terminates BOTH children before exiting.

Usage:
    python start_app.py             # start both (default)
    python start_app.py --server    # start Django only (no agent)
    python start_app.py --agent     # start agent only (server already running)
"""

import sys
import time
import socket
import subprocess
import signal
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_DIR    = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe"   # Windows venv

# Fall back to plain "python" if the venv executable isn't found
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

DJANGO_CMD = [PYTHON, "manage.py", "runserver", "--noreload"]
AGENT_CMD  = [PYTHON, "desktop_agent.py"]

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
SERVER_WAIT_TIMEOUT = 30   # seconds to wait for Django to become ready


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _is_server_up(host: str, port: int) -> bool:
    """Returns True if something is listening on host:port."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _wait_for_server(host: str, port: int, timeout: int) -> bool:
    """Block until the server is ready or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_server_up(host, port):
            return True
        time.sleep(0.5)
    return False


def _terminate(proc: subprocess.Popen, name: str):
    """Gracefully terminate a child process."""
    if proc and proc.poll() is None:
        print(f"  🛑 Stopping {name}...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"  ✅ {name} stopped.")


# ---------------------------------------------------------------------------
# LAUNCH
# ---------------------------------------------------------------------------
def launch(start_server: bool = True, start_agent: bool = True):
    django_proc = None
    agent_proc  = None

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║        WorkAnalytics OS — Unified Launcher       ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    # ── Start Django ────────────────────────────────────────────────────────
    if start_server:
        print("  🚀 Starting Django server ...")
        django_proc = subprocess.Popen(
            DJANGO_CMD,
            cwd=str(BASE_DIR),
            # Keep stdout/stderr visible in the same terminal
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        print(f"  ⏳ Waiting for server at {SERVER_HOST}:{SERVER_PORT} ...")
        if _wait_for_server(SERVER_HOST, SERVER_PORT, SERVER_WAIT_TIMEOUT):
            print(f"  ✅ Django is ready!  →  http://{SERVER_HOST}:{SERVER_PORT}/api/login/\n")
        else:
            print("  ❌ Django did not start in time. Aborting.")
            _terminate(django_proc, "Django")
            sys.exit(1)

    # ── Start Desktop Agent ─────────────────────────────────────────────────
    if start_agent:
        # Agent now runs silently in the background, no need for a separate window
        print("  🤖 Starting Desktop Tracking Agent in background...")
        
        # We add -X utf8 to explicitly prevent Unicode crashes on Windows printing emojis
        AGENT_CMD = [PYTHON, "-X", "utf8", "desktop_agent.py"]
        
        agent_proc = subprocess.Popen(
            AGENT_CMD,
            cwd=str(BASE_DIR),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print("  ✅ Agent launched successfully.\n")

    print("  💡 Press Ctrl+C here to shut down everything.\n")
    print("─" * 52)

    # ── Wait & Handle Ctrl+C ───────────────────────────────────────────────
    def _shutdown(signum=None, frame=None):
        print("\n\n  ⚡ Shutdown signal received.\n")
        _terminate(agent_proc,  "Desktop Agent")
        _terminate(django_proc, "Django Server")
        print("\n  👋 WorkAnalytics OS stopped. Goodbye!\n")
        sys.exit(0)

    # Register for both SIGINT (Ctrl+C) and SIGTERM (system shutdown)
    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        # Keep the launcher alive; watch for child crashes
        while True:
            time.sleep(2)

            if django_proc and django_proc.poll() is not None:
                print("\n  ⚠️  Django server exited unexpectedly!")
                _shutdown()

            if agent_proc and agent_proc.poll() is not None:
                print("\n  ⚠️  Desktop agent exited unexpectedly!")
                # Agent crash is non-fatal — just report it
                agent_proc = None

    except KeyboardInterrupt:
        _shutdown()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="WorkAnalytics OS Unified Launcher"
    )
    parser.add_argument("--server", action="store_true",
                        help="Start Django server only (no agent)")
    parser.add_argument("--agent",  action="store_true",
                        help="Start agent only (server already running)")
    args = parser.parse_args()

    if args.server:
        launch(start_server=True,  start_agent=False)
    elif args.agent:
        launch(start_server=False, start_agent=True)
    else:
        launch(start_server=True,  start_agent=True)
