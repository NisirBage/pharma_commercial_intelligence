"""Logging setup — standard library only, no new logging framework for a
project at this scale (M6 Sec. 25/35: no Prometheus/Grafana/ELK just for
resume keywords). One call at app startup configures a single formatted
stream handler; request-level logging (endpoint, duration, request id)
is added by `app.api.middleware`, not here.
"""

import logging
import sys


def configure_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,  # re-configure cleanly if this is called more than once (e.g. in tests)
    )
    # uvicorn's own access log is independently configured and left alone;
    # only quiet down noisy third-party libraries below our chosen level.
    for noisy_logger in ("httpx", "httpcore"):
        logging.getLogger(noisy_logger).setLevel(max(level, logging.WARNING))
