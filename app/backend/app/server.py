"""Production entry point:  python -m app.server   (also used by the Windows service)

Settings come from the environment or backend\\.env (AUTOCARE_HOST, AUTOCARE_PORT, AUTOCARE_SSL_CERTFILE/KEYFILE):
Single Computer Mode : host 127.0.0.1 (default) - only this computer can connect.
Local Network Mode   : host 0.0.0.0             - other devices on the workshop network can connect.
"""
import os
import sys

import uvicorn

from app.core.config import get_settings


def build_config(log_config=uvicorn.config.LOGGING_CONFIG) -> uvicorn.Config:
    s = get_settings()
    if bool(s.ssl_certfile) != bool(s.ssl_keyfile):
        raise SystemExit("AUTOCARE_SSL_CERTFILE and AUTOCARE_SSL_KEYFILE must be set together")
    if s.ssl_certfile:
        os.environ.setdefault("AUTOCARE_COOKIE_SECURE", "true")  # cookies only over HTTPS
        get_settings.cache_clear()
    from app.main import app  # imported after the settings are final
    return uvicorn.Config(app, host=s.host, port=s.port, ssl_certfile=s.ssl_certfile, ssl_keyfile=s.ssl_keyfile,
                          log_level="info", log_config=log_config, proxy_headers=False, server_header=False,
                          timeout_graceful_shutdown=5)  # do not wait for idle keep-alive browsers when stopping


def main() -> int:
    try:
        config = build_config()
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2
    uvicorn.Server(config).run()  # one process, one worker: in-process scheduler and locks
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
