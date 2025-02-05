
import sqlite3
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
import datetime
from typing import Optional, List
import os
import json

# Initialize loggers
message_logger = logging.getLogger('message_logger')
event_logger = logging.getLogger('event_logger')

# Ensure loggers don't propagate to root logger
message_logger.propagate = False
event_logger.propagate = False

PRE_WHITELISTED_USERNAMES = [l.stripe() for l in open("secrets/pre_whitelisted_users.txt").read().split("\n")]

def setup_logging(handlers):
    """Set up logging with the provided handlers"""
    # Remove any existing handlers
    message_logger.handlers = []
    event_logger.handlers = []
    message_logger.addHandler(handlers['message'])
    event_logger.addHandler(handlers['event'])
    message_logger.setLevel(logging.INFO)
    event_logger.setLevel(logging.INFO)

class MessageDB:
    def __init__(self, dbname: str = "telegram_messages.db"):
        self.dbname = dbname
        self.logger = logging.getLogger('message_logger')
        self.conn = sqlite3.connect(self.dbname, check_same_thread=False)
        self.setup_db()

    def setup_db(self):
        # Log database initialization
        self.logger.info(f"Initializing database: {self.dbname}")
        
        try:
            # Drop existing table if it exists
            drop_table_query = "DROP TABLE IF EXISTS messages"
            self.conn.execute(drop_table_query)
            
            create_table_query = """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY,
                    chat_id INTEGER,
                    user_id INTEGER,
                    username TEXT,
                    message_type TEXT,
                    content TEXT,
                    file_id TEXT,
                    date INTEGER,
                    reply_to_message_id INTEGER,
                    is_bot BOOLEAN DEFAULT FALSE
                )
            """
            self.conn.execute(create_table_query)
            self.conn.commit()
            self.logger.info("Database setup completed successfully")
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")
            raise

    def store_message(self, message) -> None:
        """Store a message in the database with enhanced logging"""
        try:
            message_type = "text"
            content = message.text if message.text else ""
            file_id = None

            if message.photo:
                message_type = "photo"
                file_id = message.photo[-1].file_id
                content = message.caption if message.caption else ""
            elif message.document:
                message_type = "document"
                file_id = message.document.file_id
                content = message.caption if message.caption else ""

            reply_to = message.reply_to_message.message_id if message.reply_to_message else None
            date_ts = int(message.date.timestamp())
            
            from_user = message.from_user
            username = from_user.username if from_user else None
            is_bot = from_user.is_bot if from_user else False

            # Create preview of content
            content_preview = (content[:47] + '...') if len(content) > 50 else content
            
            # Log message details with preview
            self.logger.info(
                f"Storing message: ID={message.message_id}, "
                f"Type={message_type}, User={username}, Bot={is_bot}, "
                f"Chat={message.chat_id}, "
                f"Content='{content_preview}'"
            )

            self.conn.execute(
                """
                INSERT OR REPLACE INTO messages 
                (message_id, chat_id, user_id, username, message_type, content, 
                file_id, date, reply_to_message_id, is_bot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.chat_id,
                    from_user.id if from_user else None,
                    username,
                    message_type,
                    content,
                    file_id,
                    date_ts,
                    reply_to,
                    is_bot
                ),
            )
            self.conn.commit()
            
            self.logger.info(f"Successfully stored message {message.message_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing message {message.message_id}: {e}")
            raise
    def get_messages_in_chat_since(self, chat_id: int, timestamp: int) -> List[str]:
        """
        Retrieve messages from a specific chat since a given timestamp.
        
        Args:
            chat_id (int): The ID of the chat to fetch messages from
            timestamp (int): Unix timestamp to fetch messages after
            
        Returns:
            List[str]: List of message contents formatted as "Username: Message"
        """
        try:
            self.logger.info(f"Fetching messages for chat {chat_id} since timestamp {timestamp}")
            
            query = """
                SELECT username, content
                FROM messages
                WHERE chat_id = ? 
                AND date >= ?
                AND content != ''
                ORDER BY date ASC
            """
            
            cursor = self.conn.execute(query, (chat_id, timestamp))
            messages = cursor.fetchall()
            
            # Format messages as "Username: Message"
            formatted_messages = []
            for username, content in messages:
                # Use 'Anonymous' if username is None
                display_name = username if username else 'Anonymous'
                formatted_messages.append(f"{display_name}: {content}")
            
            self.logger.info(f"Retrieved {len(formatted_messages)} messages")
            return formatted_messages
            
        except Exception as e:
            self.logger.error(f"Error fetching messages: {e}")
            raise

async def handle_art_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /art command for generating images based on text prompts"""
    if not is_authorized(update.effective_user, update.effective_chat):
        reply_message = await update.message.reply_text("You are not authorized to use this bot.")
        await store_bot_message(reply_message)
        return

    # Extract prompt (everything after /art)
    prompt = update.message.text[5:].strip()
    if not prompt:
        reply_message = await update.message.reply_text(
            "Please provide a prompt after /art command. Example: /art sunset over mountains"
        )
        await store_bot_message(reply_message)
        return

    try:
        # Send processing message
        processing_msg = await update.message.reply_text("🎨 Generating art... This may take a moment.")
        
        # Generate art in the background
        loop = asyncio.get_event_loop()
        from .art_generator import generate_art
        image_bytes = await loop.run_in_executor(None, generate_art, prompt)
        
        # Delete the processing message
        await processing_msg.delete()
        
        if image_bytes:
            # Send the image bytes with the original prompt as caption
            event_logger.info(f"Successfully generated art for prompt: {prompt[:100]}...")
            reply_message = await update.message.reply_photo(
                photo=image_bytes,
                caption=f"🎨 Generated from prompt: {prompt}"
            )
        else:
            event_logger.error(f"Failed to generate art for prompt: {prompt[:100]}...")
            reply_message = await update.message.reply_text(
                "Sorry, I couldn't generate the art. Please try again later."
            )
        
        await store_bot_message(reply_message)
        
    except Exception as e:
        event_logger.error(f"Error in art generation: {e}")
        error_message = await update.message.reply_text(
            "An error occurred while generating the art. Please try again later."
        )
        await store_bot_message(error_message)

# Initialize database
message_db = MessageDB()

def is_authorized(user, chat) -> bool:
    """Check if a user or chat is authorized to use the bot"""
    WHITELIST_FILE = "secrets/whitelist.json"
    
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, 'r') as f:
            whitelist = json.load(f)
    else:
        whitelist = {"users": [], "groups": []}

    return (
        str(user.id) in whitelist["users"] or 
        user.username in PRE_WHITELISTED_USERNAMES or
        (chat and str(chat.id) in whitelist["groups"])
    )

async def handle_px_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /px command"""
    from .perplexity_api import get_perplexity_response
    
    if not is_authorized(update.effective_user, update.effective_chat):
        reply_message = await update.message.reply_text("You are not authorized to use this bot.")
        await store_bot_message(reply_message)
        return

    # Extract query (everything after /px )
    query = update.message.text[4:].strip()
    if not query:
        reply_message = await update.message.reply_text("Please provide a query after /px.")
        await store_bot_message(reply_message)
        return

    try:
        processing_msg = await update.message.reply_text("Processing your query...")
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, get_perplexity_response, query)
        await processing_msg.delete()
        reply_message = await update.message.reply_text(reply)
        await store_bot_message(reply_message)
    except Exception as e:
        event_logger.error(f"Error in perplexity API call: {e}")
        error_message = await update.message.reply_text("An error occurred while processing your request.")
        await store_bot_message(error_message)

async def handle_summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /summarize command"""
    from .summarizer import summarize_chat

    if not is_authorized(update.effective_user, update.effective_chat):
        reply_message = await update.message.reply_text("You are not authorized to use this bot.")
        await store_bot_message(reply_message)
        return

    # Parse hours argument if present (default to 3)
    parts = update.message.text.split()
    try:
        hours = int(parts[1]) if len(parts) > 1 else 3
    except ValueError:
        reply_message = await update.message.reply_text("Please provide a valid number of hours (e.g., /summarize 4)")
        await store_bot_message(reply_message)
        return

    # Calculate timestamp for X hours ago
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    since_ts = int(since.timestamp())

    # Fetch messages
    loop = asyncio.get_event_loop()
    messages = await loop.run_in_executor(
        None, 
        message_db.get_messages_in_chat_since,
        update.effective_chat.id,
        since_ts
    )

    if not messages:
        reply_message = await update.message.reply_text(f"No messages found from the past {hours} hour(s).")
        await store_bot_message(reply_message)
        return

    try:
        processing_msg = await update.message.reply_text("Generating summary...")
        summary = await loop.run_in_executor(None, summarize_chat, messages)
        await processing_msg.delete()
        reply_message = await update.message.reply_text(f"Summary of the past {hours} hour(s):\n\n{summary}")
        await store_bot_message(reply_message)
    except Exception as e:
        event_logger.error(f"Error generating summary: {e}")
        error_message = await update.message.reply_text("An error occurred while generating the summary.")
        await store_bot_message(error_message)

async def store_bot_message(message) -> None:
    """Store a bot message in the database"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, message_db.store_message, message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main message handler that:
    1. Stores all messages
    2. Processes commands if present
    """
    if not update.message:
        return

    # Store the incoming message
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, message_db.store_message, update.message)

    # If no text content, we're done
    if not update.message.text:
        return

    # Check for commands
    text = update.message.text.strip()
    
    if text.startswith('/px '):
        await handle_px_command(update, context)
    elif text.startswith('/summarize'):
        await handle_summarize_command(update, context)
    elif text.startswith('/art'):
        event_logger.info(f"Processing /art command: {text[:50]}...")
        await handle_art_command(update, context)