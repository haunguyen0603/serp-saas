import uvicorn

from app.core.config import get_settings
from app.core.logging import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging()
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.backend_host,
        port=settings.backend_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
