import logging

_DEF_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

_configured = False

def configure(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(level=level, format=_DEF_FORMAT)
    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    if not _configured:
        configure()
    return logging.getLogger(name or __name__)
