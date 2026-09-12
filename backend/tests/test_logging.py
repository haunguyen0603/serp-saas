import json
import logging

from app.core.logging import JSONFormatter


def test_structured_logging_does_not_serialize_exception() -> None:
    record = logging.LogRecord("app.requests", logging.INFO, "", 0, "Request", (), None)
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration = 0.01
    payload = json.loads(JSONFormatter().format(record))
    assert set(payload) == {
        "timestamp",
        "level",
        "logger",
        "message",
        "method",
        "path",
        "status_code",
        "duration",
    }
