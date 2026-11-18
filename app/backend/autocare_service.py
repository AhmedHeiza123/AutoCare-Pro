"""Windows service wrapper for AutoCare Pro (needs the `pywin32` package; Windows only).

Run in an ADMINISTRATOR terminal from the backend folder:
    python autocare_service.py install      # registers service "AutoCarePro" (automatic start, restarts itself on failure)
    python autocare_service.py start | stop | restart | remove
    python autocare_service.py debug        # after install: run in the console exactly as the service would (stop with Ctrl+C)
    python autocare_service.py status

The service runs the same web server as `python -m app.server` (settings from backend\\.env) and shuts it down gracefully
on stop, so in-flight requests finish before PostgreSQL connections are closed.
"""
import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
SERVICE_NAME = "AutoCarePro"
DISPLAY_NAME = "AutoCare Pro (workshop management)"
DESCRIPTION = "AutoCare Pro web server for the workshop. Starts automatically with Windows."


def _logger() -> logging.Logger:
    log_dir = Path(os.environ.get("AUTOCARE_STORAGE_DIR", BACKEND_DIR / "storage")) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    lg = logging.getLogger("autocare.service")
    if not lg.handlers:
        h = RotatingFileHandler(log_dir / "service.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        lg.addHandler(h)
        lg.setLevel(logging.INFO)
    return lg


class ServerRunner:
    """Runs uvicorn in a worker thread and can stop it gracefully."""

    def __init__(self) -> None:
        self.server = None
        self.error: BaseException | None = None
        self.thread: threading.Thread | None = None
        self.started = threading.Event()

    def _run(self) -> None:
        try:
            os.chdir(BACKEND_DIR)  # relative paths in .env (e.g. storage/certs) resolve from here
            if sys.stdout is None or sys.stderr is None:  # libraries that print/inspect the console must not crash
                sys.stdout = sys.stderr = open(os.devnull, "w")
            sys.path.insert(0, str(BACKEND_DIR))
            import uvicorn

            from app.server import build_config
            # a service has no console (sys.stderr is None): uvicorn must not configure console logging
            logging.getLogger("uvicorn").handlers[:] = [h for h in _logger().handlers]
            logging.getLogger("uvicorn.error").handlers[:] = [h for h in _logger().handlers]
            cfg = build_config(log_config=None)
            self.server = uvicorn.Server(cfg)
            self.started.set()
            self.server.run()
        except BaseException as e:  # noqa: BLE001 - reported to the service manager
            self.error = e
            _logger().exception("server crashed")
        finally:
            self.started.set()

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, name="autocare-web", daemon=True)
        self.thread.start()
        self.started.wait(30)

    def stop(self, timeout: float = 30) -> None:
        if self.server is not None:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout)


try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil

    class AutoCareService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = DISPLAY_NAME
        _svc_description_ = DESCRIPTION

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.runner = ServerRunner()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, waitHint=35000)
            _logger().info("stop requested")
            self.runner.stop()
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            lg = _logger()
            lg.info("starting AutoCare Pro service")
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ""))
            self.runner.start()
            if self.runner.error is not None:  # e.g. bad .env: fail loudly so the SCM restarts/reports it
                lg.error("startup failed: %s", self.runner.error)
                self.ReportServiceStatus(win32service.SERVICE_STOPPED, win32ExitCode=1)
                return
            # wait until asked to stop OR the web server thread ends unexpectedly
            while True:
                rc = win32event.WaitForSingleObject(self.stop_event, 2000)
                if rc == win32event.WAIT_OBJECT_0:
                    break
                if self.runner.thread and not self.runner.thread.is_alive():
                    lg.error("web server stopped unexpectedly")
                    self.ReportServiceStatus(win32service.SERVICE_STOPPED, win32ExitCode=2)  # non-zero => recovery actions restart it
                    return
            lg.info("AutoCare Pro service stopped")
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STOPPED, (self._svc_name_, ""))

    HAVE_PYWIN32 = True
except ImportError:  # not on Windows / pywin32 missing
    HAVE_PYWIN32 = False


def _post_install() -> None:
    """Automatic (delayed) start + restart on failure, so a crash or reboot never leaves the workshop without the system."""
    import subprocess
    subprocess.run(["sc.exe", "config", SERVICE_NAME, "start=", "delayed-auto"], check=False)
    subprocess.run(["sc.exe", "failure", SERVICE_NAME, "reset=", "86400", "actions=", "restart/5000/restart/15000/restart/60000"], check=False)
    subprocess.run(["sc.exe", "failureflag", SERVICE_NAME, "1"], check=False)  # also restart on non-zero exit codes


def main(argv: list[str]) -> int:
    if not HAVE_PYWIN32:
        print("pywin32 is required: pip install pywin32  (Windows only)")
        return 2
    if len(argv) == 1:  # started by the service control manager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AutoCareService)
        servicemanager.StartServiceCtrlDispatcher()
        return 0
    cmd = argv[1].lower()
    if cmd == "status":
        import win32serviceutil as su
        try:
            state = su.QueryServiceStatus(SERVICE_NAME)[1]
            print({1: "stopped", 2: "starting", 3: "stopping", 4: "running"}.get(state, state))
            return 0
        except Exception:  # noqa: BLE001
            print("not installed")
            return 1
    rc = win32serviceutil.HandleCommandLine(AutoCareService, argv=argv)
    if cmd == "install":
        _post_install()
    return rc or 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
