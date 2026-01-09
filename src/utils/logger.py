"""Structured logging configuration using Loguru"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(
    log_dir: str = "logs",
    level: str = "INFO",
    rotation: str = "daily",
    retention_days: int = 30
) -> None:
    """Configure structured logger with rotation

    Args:
        log_dir: Directory for log files
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        rotation: Rotation frequency (hourly, daily, weekly)
        retention_days: Number of days to retain logs
    """
    # Remove default handler
    logger.remove()

    # Add console handler with color
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )

    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Determine rotation schedule
    rotation_schedule = {
        "hourly": "1 hour",
        "daily": "1 day",
        "weekly": "1 week"
    }.get(rotation, "1 day")

    # Add file handler with rotation
    logger.add(
        log_path / "fiftyfive_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation=rotation_schedule,
        retention=f"{retention_days} days",
        compression="zip",
        enqueue=True,  # Async-safe
        backtrace=True,
        diagnose=True
    )

    logger.info(f"Logger initialized: level={level}, dir={log_dir}, rotation={rotation}")


def get_logger():
    """Get logger instance"""
    return logger
