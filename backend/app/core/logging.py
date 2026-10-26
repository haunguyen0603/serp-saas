import json
import logging
import logging.config
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in (
            "alert_type",
            "delivery_id",
            "delivery_status",
            "attempts",
            "evaluated_count",
            "delivered_count",
            "payment_order_id",
            "invoice_number",
            "notification_type",
            "provider_transaction_id",
            "status_transition",
            "batch_id",
            "job_id",
            "worker_execution_id",
            "attempt_count",
            "trigger_type",
            "duration_ms",
            "safe_error_code",
            "method",
            "path",
            "status_code",
            "duration",
            "project_id",
            "keyword_id",
            "tracked_site_id",
            "user_id",
            "rank_check_id",
            "provider",
            "attempt",
            "error_code",
            "result_count",
            "match_count",
            "submitted",
            "created_count",
        ):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        # Exception text can contain credentials; never serialize it.
        return json.dumps(payload)


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JSONFormatter}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"level": "INFO", "handlers": ["console"]},
            "loggers": {
                "uvicorn": {"handlers": ["console"], "propagate": False},
                "uvicorn.error": {"handlers": ["console"], "propagate": False},
                "uvicorn.access": {"handlers": [], "propagate": False},
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )
