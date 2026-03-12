"""Configure a logger using a dictionary."""

from __future__ import annotations

import logging
import logging.config

# Formatters: change what gets logged
minimal = "%(message)s"
detailed = "%(asctime)s | %(process)d | %(levelname)s | %(name)s | %(message)s "
formatters = {"minimal": {"format": minimal}, "detailed": {"format": detailed}}


class Logger:
    """Get logger and set console and file outputs.

    Args:
        file_name: Path for file logging output
        file_format: Format type for file output ('minimal' or 'detailed')
        file_mode: File open mode
        console: Whether to enable console logging
        console_format: Format type for console output ('minimal' or 'detailed')
        console_level: Logging level for console output
    """

    def __init__(
        self,
        file_name: str = "",
        file_format: str = "detailed",
        file_mode: str = "w",
        console: bool = True,
        console_format: str = "detailed",
        console_level: str = "DEBUG",
    ) -> None:
        # Handlers: change file and console logging details
        handlers: dict[str, dict] = {}
        if console:
            assert console_format in formatters, (
                f"Must select formatting type from {list(formatters.keys())}"
            )

            handlers["console_handle"] = {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": console_format,
            }

        if file_name:
            assert isinstance(file_name, str), "Must provide name for file logging"
            assert file_format in formatters, (
                f"Must select formatting type from {list(formatters.keys())}"
            )

            handlers["file_handle"] = {
                "class": "logging.FileHandler",
                "level": "INFO",
                "formatter": file_format,
                "filename": file_name,
                "mode": file_mode,
            }

        # Loggers: change logging options for root and other packages
        loggers = {
            # Package logger (not root)
            "suggests": {
                "handlers": list(handlers.keys()),
                "level": "DEBUG",
                "propagate": False,
            },
            # External loggers
            "requests": {"level": "WARNING"},
            "urllib3": {"level": "WARNING"},
            "matplotlib": {"level": "WARNING"},
            "chardet.charsetprober": {"level": "INFO"},
            "parso": {"level": "INFO"},  # Fix for ipython autocomplete bug
        }

        self.log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatters,
            "handlers": handlers,
            "loggers": loggers,
        }

    def start(self, name: str = "suggests") -> logging.Logger:
        """Initialize and return a named logger.

        Args:
            name: Logger name

        Returns:
            Configured logger instance
        """
        logging.config.dictConfig(self.log_config)
        return logging.getLogger(name)
