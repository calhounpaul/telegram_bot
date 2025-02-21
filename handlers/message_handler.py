import sqlite3
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
import datetime
from typing import Optional, List
import os
import json
from .summarizer import summarize_research
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize loggers
message_logger = logging.getLogger('message_logger')
event_logger = logging.getLogger('event_logger')

# Ensure loggers don't propagate to root logger
message_logger.propagate = False
event_logger.propagate = False

PRE_WHITELISTED_USERNAMES = os.getenv("PRE_WHITELISTED_USERS", "").split(",")

WHITELIST_FILE = "whitelist.json"
SUMMARIZE_RESEARCH=os.getenv("SUMMARIZE_RESEARCH")
RESEARCH_COMMAND = "/" + os.getenv("RESEARCH_COMMAND")
ART_COMMAND = "/" + os.getenv("ART_COMMAND")
SUMMARIZE_COMMAND = "/" + os.getenv("SUMMARIZE_COMMAND")
WHITELIST_USER_COMMAND="/" + os.getenv("WHITELIST_USER_COMMAND")
WHITELIST_GROUP_COMMAND="/" + os.getenv("WHITELIST_GROUP_COMMAND")

def load_whitelist() -> dict:
    """Load the whitelist JSON file or return a default structure."""
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            message_logger.error(f"Error loading whitelist file: {e}")
    # Default structure
    return {"users": [], "groups": []}

def save_whitelist(whitelist: dict) -> None:
    """Save the whitelist dictionary back to the JSON file."""
    try:
        with open(WHITELIST_FILE, "w") as f:
            json.dump(whitelist, f, indent=4)
    except Exception as e:
        message_logger.error(f"Error saving whitelist file: {e}")

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
                SELECT username, date, content
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
            for username, date, content in messages:
                # Use 'Anonymous' if username is None
                display_name = username if username else 'Anonymous'
                formatted_messages.append(f"{display_name} ({datetime.datetime.fromtimestamp(date)}): {content}")
            
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

    prompt = update.message.text[len(ART_COMMAND):].strip()
    if not prompt:
        reply_message = await update.message.reply_text(
            "Please provide a prompt after "+ART_COMMAND+" command. Example: "+ART_COMMAND+" sunset over mountains"
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
    """
    Check if a user or chat is authorized to use the bot.
    If a user was whitelisted by username, remove that entry and add their ID.
    """
    whitelist = load_whitelist()
    
    # First, allow if the user’s Telegram ID (as a string) is already whitelisted.
    if str(user.id) in whitelist.get("users", []):
        return True

    # If the user’s username is in the whitelist (i.e. added via /whitelist),
    # update the whitelist: remove the username and add the Telegram ID.
    if user.username and user.username in whitelist.get("users", []):
        whitelist["users"].remove(user.username)
        if str(user.id) not in whitelist["users"]:
            whitelist["users"].append(str(user.id))
        save_whitelist(whitelist)
        return True

    # Allow pre-whitelisted users (from pre_whitelisted_users.txt)
    if user.username and user.username in PRE_WHITELISTED_USERNAMES:
        return True

    # Allow chats if their id is whitelisted in groups.
    if chat and str(chat.id) in whitelist.get("groups", []):
        return True

    return False

async def handle_whitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /whitelist command.
    
    Usage:
        /whitelist username1 username2 ...
    
    Only core users (pre-whitelisted or already authorized) may add new usernames.
    The command accepts usernames with or without a leading "@".
    """
    user = update.effective_user
    # Only allow this command if the issuing user is a “core” user:
    # (i.e. pre-whitelisted or already in the whitelist by ID)
    current_whitelist = load_whitelist()
    if not (
        (user.username and user.username in PRE_WHITELISTED_USERNAMES) or 
        (str(user.id) in current_whitelist.get("users", []))
    ):
        reply_message = await update.message.reply_text("You are not authorized to use this command.")
        await store_bot_message(reply_message)
        return

    # Parse command arguments (everything after "/whitelist")
    args = update.message.text.split()[1:]
    if not args:
        reply_message = await update.message.reply_text("Usage: " +WHITELIST_USER_COMMAND+ " username1 username2 ...")
        await store_bot_message(reply_message)
        return

    # Remove any leading '@' characters from the usernames.
    new_usernames = [arg.lstrip('@') for arg in args]

    # Reload whitelist (to be safe) and add each new username if not already present.
    whitelist = load_whitelist()
    added = []
    for uname in new_usernames:
        # Avoid adding if the entry already appears (either as username or as an id)
        if uname not in whitelist.get("users", []) and not uname.isdigit():
            whitelist["users"].append(uname)
            added.append(uname)

    save_whitelist(whitelist)

    if added:
        reply_message = await update.message.reply_text(f"Whitelisted usernames added: {', '.join(added)}")
    else:
        reply_message = await update.message.reply_text("No new usernames were added to the whitelist.")
    await store_bot_message(reply_message)


async def handle_research_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /research command with file attachment"""
    from io import BytesIO
    from telegram import InputFile
    from .perplexity_api import get_perplexity_response

    # Existing authorization and query handling
    if not is_authorized(update.effective_user, update.effective_chat):
        reply_message = await update.message.reply_text("Unauthorized access attempt blocked")
        await store_bot_message(reply_message)
        return

    query = update.message.text[10:].strip()
    if not query:
        reply_message = await update.message.reply_text("Query syntax: " + RESEARCH_COMMAND + " <question>")
        await store_bot_message(reply_message)
        return

    
    query = update.message.text[len(RESEARCH_COMMAND):].strip()
    if not query:
        reply_message = await update.message.reply_text("Query syntax: /prof <question>")
        await store_bot_message(reply_message)
        return

    try:
        processing_msg = await update.message.reply_text("Analyzing request...")
        loop = asyncio.get_event_loop()
        reply_full = await loop.run_in_executor(None, get_perplexity_response, query)
        if SUMMARIZE_RESEARCH==True:
            print(SUMMARIZE_RESEARCH)
            reply_summary = await loop.run_in_executor(None, summarize_research, reply_full)
            await processing_msg.delete()
            # Create in-memory text file
            text_buffer = BytesIO(reply_full.encode('utf-8'))
            
            # Send document with metadata
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=InputFile(text_buffer, filename='research_report.txt'),
                caption="Research summary:\n" + reply_summary + "\n\n(Full analysis + citations attached)",
            )
        else:
            await processing_msg.delete()
            await update.message.reply_text(reply_full)

    except Exception as e:
        event_logger.error(f"Processing failure: {str(e)}")
        error_message = await update.message.reply_text("Analysis system error")
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

async def handle_whitelist_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /whitelist_group command to whitelist the current group chat.
    When executed in a group or supergroup, it adds the group's ID to the whitelist,
    thereby allowing all members in the group to use the bot.
    """
    chat = update.effective_chat
    if not chat:
        return

    # This command is only valid in a group or supergroup.
    if chat.type not in ["group", "supergroup"]:
        reply_message = await update.message.reply_text("This command can only be used in a group chat.")
        await store_bot_message(reply_message)
        return

    whitelist = load_whitelist()
    group_id_str = str(chat.id)

    # Check if the group is already whitelisted.
    if group_id_str in whitelist.get("groups", []):
        reply_message = await update.message.reply_text("This group is already whitelisted.")
        await store_bot_message(reply_message)
        return

    # Add the group id to the whitelist.
    whitelist.setdefault("groups", []).append(group_id_str)
    save_whitelist(whitelist)

    reply_message = await update.message.reply_text(
        "Group has been successfully whitelisted. All members in this group can now use the bot."
    )
    await store_bot_message(reply_message)


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
    
    if text.startswith(RESEARCH_COMMAND):
        await handle_research_command(update, context)
    elif text.startswith(SUMMARIZE_COMMAND):
        await handle_summarize_command(update, context)
    elif text.startswith(ART_COMMAND):
        event_logger.info(f"Processing "+ART_COMMAND+" command: {text[:50]}...")
        await handle_art_command(update, context)
