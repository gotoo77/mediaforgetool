import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings  # noqa: E402

RUNTIME_DIR = Path("temp")
PID_FILE = RUNTIME_DIR / "dev-server.pid"
LOG_FILE = RUNTIME_DIR / "dev-server.log"
START_TIMEOUT_SECONDS = 15
STOP_TIMEOUT_SECONDS = 10


def read_pid() -> int | None:
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None


def write_pid(pid: int) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(f"{pid}\n", encoding="utf-8")


def remove_pid() -> None:
    PID_FILE.unlink(missing_ok=True)


def process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def server_url() -> str:
    settings = get_settings()
    return f"http://{settings.app_host}:{settings.app_port}"


def health_url() -> str:
    return f"{server_url()}/healthz"


def wait_for_health(timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(health_url(), timeout=1) as response:
                if response.status == 200:
                    return True
        except URLError:
            pass
        time.sleep(0.25)
    return False


def status() -> int:
    pid = read_pid()
    if pid is None:
        print("inactive")
        return 0
    if not process_is_running(pid):
        remove_pid()
        print("inactive (stale pid removed)")
        return 0
    health = "healthy" if wait_for_health(1) else "running"
    print(f"active ({health})")
    print(f"pid: {pid}")
    print(f"url: {server_url()}")
    print(f"log: {LOG_FILE}")
    return 0


def start() -> int:
    pid = read_pid()
    if pid is not None and process_is_running(pid):
        print(f"already active (pid {pid})")
        print(f"url: {server_url()}")
        return 0
    remove_pid()
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = LOG_FILE.open("ab")
    process = subprocess.Popen(
        [sys.executable, "-m", "app.run", "--reload"],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log_handle.close()
    write_pid(process.pid)
    if wait_for_health(START_TIMEOUT_SECONDS):
        print("started")
        print(f"pid: {process.pid}")
        print(f"url: {server_url()}")
        print(f"log: {LOG_FILE}")
        return 0
    if process.poll() is not None:
        remove_pid()
        print(f"failed to start (exit {process.returncode})")
        print(f"log: {LOG_FILE}")
        return process.returncode or 1
    print("started, healthcheck pending")
    print(f"pid: {process.pid}")
    print(f"url: {server_url()}")
    print(f"log: {LOG_FILE}")
    return 0


def stop() -> int:
    pid = read_pid()
    if pid is None:
        print("inactive")
        return 0
    if not process_is_running(pid):
        remove_pid()
        print("inactive (stale pid removed)")
        return 0
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        remove_pid()
        print("inactive")
        return 0
    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not process_is_running(pid):
            remove_pid()
            print("stopped")
            return 0
        time.sleep(0.25)
    os.killpg(pid, signal.SIGKILL)
    remove_pid()
    print("stopped (forced)")
    return 0


def restart() -> int:
    stop_code = stop()
    if stop_code != 0:
        return stop_code
    return start()


def logs() -> int:
    if not LOG_FILE.exists():
        print(f"no log yet: {LOG_FILE}")
        return 0
    subprocess.run(["tail", "-n", "80", str(LOG_FILE)], check=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the MediaForgeTool dev server.")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "logs"])
    return parser


def main() -> None:
    args = build_parser().parse_args()
    handlers = {
        "start": start,
        "stop": stop,
        "restart": restart,
        "status": status,
        "logs": logs,
    }
    raise SystemExit(handlers[args.command]())


if __name__ == "__main__":
    main()
