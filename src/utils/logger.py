"""
Logging configuration and utilities
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "subdomain_takeover",
    verbose: bool = False,
    debug: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup and configure logger

    Args:
        name: Logger name
        verbose: Enable verbose output
        debug: Enable debug output
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    # Determine log level
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create simple formatter
    formatter = logging.Formatter('%(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # Always log debug to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance by name

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(f"subdomain_takeover.{name}")
