import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors based on the logging level."""

    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    COLORS = {
        logging.DEBUG: RESET,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: MAGENTA + BOLD,
    }

    def format(self, record):
        log_message = super().format(record)
        color = self.COLORS.get(record.levelno, self.RESET)
        return f"{color}{log_message}{self.RESET}"


class LoggerSetup:
    """Setup logging with colored output for the entire application."""

    @staticmethod
    def setup(log_level=logging.INFO, log_format="%(asctime)s [%(levelname)s]\t %(name)s\t: %(message)s"):
        """
        Configure logging with colored output

        Args:
            log_level: The logging level (default: logging.INFO)
            log_format: The format string for log messages

        Returns:
            The root logger instance
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicate logs
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Create formatter
        formatter = ColoredFormatter(log_format)
        console_handler.setFormatter(formatter)

        # Add handler to logger
        root_logger.addHandler(console_handler)

        return root_logger

    @staticmethod
    def get_logger(name):
        """
        Get a logger with the specified name.

        Args:
            name: The logger name (typically __name__ from the calling module)

        Returns:
            A configured logger instance
        """
        return logging.getLogger(name)


# # Example usage:
# if __name__ == "__main__":
#     # Setup the root logger
#     LoggerSetup.setup(log_level=logging.DEBUG)

#     # Get a logger for this module
#     logger = LoggerSetup.get_logger(__name__)

#     # Test different log levels
#     logger.debug("This is a DEBUG message")
#     logger.info("This is an INFO message")
#     logger.warning("This is a WARNING message")
#     logger.error("This is an ERROR message")
#     logger.critical("This is a CRITICAL message")
