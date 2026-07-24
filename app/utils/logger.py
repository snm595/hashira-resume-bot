"""
Centralized structured logging configuration.

Design Decision:
    Every module in this application gets its own named logger via get_logger().
    This satisfies PRD §16: "Every module logs independently."

    We use Python's built-in logging module with:
    - Console handler (StreamHandler) for development visibility.
    - File handler (RotatingFileHandler) for production audit trail.
    - Structured format with timestamp, module name, level, and message.

    RotatingFileHandler is used instead of plain FileHandler to prevent
    unbounded log file growth in production.

Usage:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Processing resume", extra={"filename": "resume.pdf"})
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


# ---------------------------------------------------------------------------
# Module-level flag to ensure handlers are only attached once,
# even if get_logger() is called multiple times for the same root.
# ---------------------------------------------------------------------------
_root_configured: bool = False


def setup_root_logger(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """
    Configure the root logger with console and file handlers.

    This should be called ONCE during application startup. All child loggers
    created via get_logger() inherit this configuration.

    Args:
        log_level: The minimum logging level (e.g., "INFO", "DEBUG").
        log_dir: Directory path for log file output.
    """
    global _root_configured
    if _root_configured:
        return

    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Define a consistent format across all handlers
    # Format: [2024-01-15 10:30:45] [INFO] [app.parser.pdf_parser] Parsing document...
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Console Handler ---
    # Outputs to stderr so it doesn't interfere with stdout piping
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(formatter)

    # --- File Handler ---
    # RotatingFileHandler: max 5MB per file, keep 3 backups
    # This prevents unbounded log growth in production
    file_handler = RotatingFileHandler(
        filename=log_path / "app.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # --- Configure Root Logger ---
    root_logger = logging.getLogger("app")
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Prevent log propagation to the default root logger
    # which would cause duplicate output
    root_logger.propagate = False

    _root_configured = True


def get_logger(module_name: str) -> logging.Logger:
    """
    Get a named logger for a specific module.

    Each module should call this with __name__ to get a logger scoped
    to that module. The logger inherits configuration from the root
    'app' logger set up by setup_root_logger().

    Args:
        module_name: The fully qualified module name (typically __name__).

    Returns:
        A configured Logger instance for the given module.

    Example:
        logger = get_logger(__name__)  # e.g., "app.parser.pdf_parser"
        logger.info("Extracted 3 pages from document")
    """
    return logging.getLogger(module_name)
