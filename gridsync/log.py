import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from twisted.python.log import PythonLoggingObserver, startLogging

from gridsync import APP_NAME, config_dir, settings

_logging_path = settings.get("logging", {}).get("path")
if _logging_path:
    LOGS_PATH = Path(_logging_path)
else:
    LOGS_PATH = Path(config_dir, "logs")


class LogFormatter(logging.Formatter):
    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        return datetime.now(timezone.utc).isoformat()


def make_file_logger(
    name: Optional[str] = None,
    max_bytes: int = 10_000_000,
    backup_count: int = 1,
    fmt: Optional[str] = "%(asctime)s %(levelname)s %(funcName)s %(message)s",
    use_null_handler: bool = False,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    LOGS_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)

    if not name:
        name = APP_NAME

    handler: Union[logging.NullHandler, RotatingFileHandler]
    if use_null_handler:
        handler = logging.NullHandler()
    else:
        handler = RotatingFileHandler(
            Path(LOGS_PATH, f"{name}.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
    if fmt:
        handler.setFormatter(LogFormatter(fmt=fmt))
    logger.addHandler(handler)
    return logger


def initialize_logger(
    to_stdout: bool = False, use_null_handler: bool = False
) -> None:
    logger = make_file_logger(use_null_handler=use_null_handler)
    formatter = LogFormatter(
        fmt="%(asctime)s %(levelname)s %(funcName)s %(message)s"
    )

    if to_stdout:
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)
        startLogging(sys.stdout)

    observer = PythonLoggingObserver()
    observer.start()
    logging.debug("Hello World!")


def find_log_files(pattern: str = "*.log*") -> list[Path]:
    return sorted([path for path in LOGS_PATH.glob(pattern) if path.is_file()])


def read_log_messages(path: Path) -> list[str]:
    try:
        return [line for line in path.read_text("utf-8").split("\n") if line]
    except FileNotFoundError:
        return []


class MultiFileLogger:
    def __init__(self, basename: str) -> None:
        self.basename = basename
        self._loggers: dict[str, logging.Logger] = {}

    def log(
        self, logger_name: str, message: str, omit_fmt: bool = False
    ) -> None:
        name = f"{self.basename}.{logger_name}"
        logger = self._loggers.get(name)
        if not logger:
            if omit_fmt:
                logger = make_file_logger(name, fmt=None)
            else:
                logger = make_file_logger(name)
            self._loggers[name] = logger
        logger.debug(message)

    def read_messages(self, logger_name: str) -> list[str]:
        messages = []
        for p in find_log_files(f"{self.basename}.{logger_name}.log*"):
            messages.extend(read_log_messages(p))
        return messages


class NullLogger:
    def log(
        self, logger_name: str, message: str, omit_fmt: bool = False
    ) -> None:
        pass

    def read_messages(self, logger_name: str) -> list:
        return []
