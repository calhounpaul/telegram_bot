import logging
from logging.handlers import RotatingFileHandler
import os
from handlers.message_handler import handle_message
from handlers import setup_logging
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
from handlers.message_handler import handle_message, handle_whitelist_command, handle_whitelist_group_command
from handlers import setup_logging
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WHITELIST_USER_COMMAND=os.getenv("WHITELIST_USER_COMMAND")
WHITELIST_GROUP_COMMAND=os.getenv("WHITELIST_GROUP_COMMAND")

class BotLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up file handlers
        self.setup_file_handlers()
        
        # Configure root logger
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            handlers=[self.console_handler]
        )
        
        # Get logger instance
        self.logger = logging.getLogger(__name__)
        
    def setup_file_handlers(self):
        # Console handler
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(logging.INFO)
        
        # Message log handler (10MB max size, 5 backup files)
        message_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'messages.log'),
            maxBytes=10*1024*1024,
            backupCount=5
        )
        message_handler.setLevel(logging.INFO)
        
        # Event log handler
        event_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'events.log'),
            maxBytes=10*1024*1024,
            backupCount=5
        )
        event_handler.setLevel(logging.INFO)
        
        # Error log handler
        error_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'errors.log'),
            maxBytes=10*1024*1024,
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Set formatters
        for handler in [message_handler, event_handler, error_handler, self.console_handler]:
            handler.setFormatter(formatter)
        
        # Store handlers
        self.handlers = {
            'message': message_handler,
            'event': event_handler,
            'error': error_handler
        }

def main():
    # Initialize logger
    bot_logger = BotLogger()
    logger = bot_logger.logger

    logger.info("Initializing bot application...")

    # Initialize bot with custom event logging
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Set up logging handlers in message handler
    setup_logging.setup_logging(bot_logger.handlers)
    
    # Add the whitelist command handler for individual users.
    application.add_handler(CommandHandler(WHITELIST_USER_COMMAND, handle_whitelist_command))
    
    # Add the new whitelist_group command handler.
    application.add_handler(CommandHandler(WHITELIST_GROUP_COMMAND, handle_whitelist_group_command))
    
    # Then add the generic message handler (for other commands and messages)
    application.add_handler(MessageHandler(filters.ALL, handle_message))
    
    logger.info("Bot initialized successfully. Starting polling...")
    
    # Start the bot
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Error during bot execution: {e}")
        raise

if __name__ == "__main__":
    main()
