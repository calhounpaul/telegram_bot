import logging
from typing import Dict
from logging.handlers import RotatingFileHandler

def setup_logging(handlers: Dict[str, RotatingFileHandler]) -> None:
    """
    Set up logging configuration with the provided handlers.
    
    Args:
        handlers (Dict[str, RotatingFileHandler]): Dictionary containing logging handlers
            with keys 'message', 'event', and 'error'
    """
    # Initialize loggers
    message_logger = logging.getLogger('message_logger')
    event_logger = logging.getLogger('event_logger')
    error_logger = logging.getLogger('error_logger')
    
    # Ensure loggers don't propagate to root logger
    message_logger.propagate = False
    event_logger.propagate = False
    error_logger.propagate = False
    
    # Clear any existing handlers
    message_logger.handlers = []
    event_logger.handlers = []
    error_logger.handlers = []
    
    # Add appropriate handlers to each logger
    message_logger.addHandler(handlers['message'])
    event_logger.addHandler(handlers['event'])
    error_logger.addHandler(handlers['error'])
    
    # Set logging levels
    message_logger.setLevel(logging.INFO)
    event_logger.setLevel(logging.INFO)
    error_logger.setLevel(logging.ERROR)
    
    # Log initialization
    message_logger.info("Message logging initialized")
    event_logger.info("Event logging initialized")
    error_logger.info("Error logging initialized")