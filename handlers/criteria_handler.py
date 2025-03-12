# File: handlers/criteria_handler.py

import logging
import re
import asyncio
from typing import Dict, List
import os
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ContextTypes

# Reuse the same LLM client from summarizer (Hyperbolic-based openai-like client).
from .summarizer import llama_client, MODEL_NAME, MSG_SEPARATOR, MAX_CHARS
from .perplexity_api import get_perplexity_response
from .message_handler import message_db  # We need DB access to fetch recent messages

load_dotenv()

DISABLE_AUTO_RESPONSES = os.getenv("DISABLE_AUTO_RESPONSES", "0").strip().lower() in ["1", "true"]

# Criteria in natural language, e.g.:
#   "If the user explicitly requests help or has a question about code, say YES: <question>, else NO."
CRITERIA_NL = os.getenv("CRITERIA_NL", "If the user explicitly requests help or has a question about code, say 'YES: <question>', else NO.")

# Comma-separated keywords that will automatically trigger a Perplexity search
# e.g. "urgent,help,python"
CRITERIA_KEYWORDS = os.getenv("CRITERIA_KEYWORDS", "")

# Split the keywords into a list of lowercase strings for quick scanning:
KEYWORDS_LIST = [k.strip().lower() for k in CRITERIA_KEYWORDS.split(",") if k.strip()]

# We maintain conversation data in-memory to periodically generate a summary.
# Example structure:
# conversation_data[chat_id] = {
#     "message_count": int,
#     "summary": str,
#     "messages_for_summary": [("username", "some message text"), ...]
# }
conversation_data: Dict[int, Dict] = {}

# Configure a logger for this new handler
criteria_logger = logging.getLogger("criteria_logger")
criteria_logger.propagate = False

async def handle_criteria_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This handler is called after each new message is stored.
    1. Keeps a rolling summary every N=10 messages (using the same LLM approach as summarizer).
    2. For each new message, checks if any of the user-specified keywords are present.
       - If a keyword match is found, we do an immediate Perplexity search using the
         entire new message text, then send the bot's reply.
       - Otherwise, we ask the LLM if this message meets the user-provided CRITERIA_NL.
         The LLM must answer either "YES: <query>" or "NO".
         If "YES," the <query> part is used as a prompt to Perplexity, and the bot replies
         with the search result in chat.
    """
    if DISABLE_AUTO_RESPONSES:
        return
    if not update.message:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    user_name = user.username if user and user.username else "Anonymous"
    message_text = update.message.text or ""
    message_text_lower = message_text.lower().strip()

    # 1. Update rolling summary data.
    maintain_criteria_summary(chat_id, user_name, message_text)

    # 2. Check for direct keyword triggers first.
    triggered_by_keyword = False
    if KEYWORDS_LIST:
        for kw in KEYWORDS_LIST:
            if kw in message_text_lower:
                triggered_by_keyword = True
                break

    if triggered_by_keyword:
        # Use the entire new message as the query to Perplexity.
        await reply_with_perplexity(context, update, query=message_text)
        return

    # 3. If not triggered by keyword, ask the LLM to see if it meets the CRITERIA_NL.
    conversation_summary = conversation_data[chat_id].get("summary", "")
    # Build an LLM prompt. We instruct the model to output *only* "YES: <some query>" or "NO"
    prompt = f"""
We have a conversation summary so far:
{conversation_summary}

A new user message from {user_name} is:
\"{message_text}\"

We have the following criteria:
{CRITERIA_NL}

Respond ONLY with:
  YES: <some query here>   (if the criteria is met)
  NO                       (if criteria not met)
No extra text, no explanation.
"""

    try:
        # Instead of passing a dictionary to create(...), we wrap it in a lambda:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: llama_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.7,
                top_p=0.95
            )
        )
        text_response = response.choices[0].message.content.strip()
        criteria_logger.info(f"Criteria-check LLM response: {text_response}")

        # 4. If the model says "YES: <query>", parse <query> and call Perplexity
        if text_response.startswith("YES:"):
            query_part = text_response[4:].strip()
            # If the LLM gave no query, use entire message as fallback
            if not query_part:
                query_part = message_text
            await reply_with_perplexity(context, update, query=query_part)

        # If the model says "NO", do nothing.
    except Exception as e:
        criteria_logger.error(f"Error during criteria LLM check: {e}")


def maintain_criteria_summary(chat_id: int, username: str, message_text: str) -> None:
    """
    Maintain a rolling conversation summary for each chat.
    Every 10 messages, update the summary using the same approach as summarizer.
    """
    # Lazy init
    if chat_id not in conversation_data:
        conversation_data[chat_id] = {
            "message_count": 0,
            "summary": "",
            "messages_for_summary": [],
        }

    conversation_data[chat_id]["message_count"] += 1
    conversation_data[chat_id]["messages_for_summary"].append((username, message_text))

    # Once we have 10 new messages, build a new summary.
    if conversation_data[chat_id]["message_count"] % 10 == 0:
        # We'll gather all messages into a text block up to MAX_CHARS length
        all_messages = []
        for (usernm, text) in conversation_data[chat_id]["messages_for_summary"]:
            all_messages.append(f"{usernm}: {text}")
        # Construct a single string:
        chat_text = MSG_SEPARATOR.join(all_messages)[-MAX_CHARS:]

        # Summarize with the same approach as summarizer.summarize_chat:
        prompt = (
            f"Summarize the following chat:\n####CHAT_BEGIN####{chat_text}\n####CHAT_END####\n"
            "Your summary should be no larger than two paragraphs of 4 sentences each."
        )
        try:
            response = llama_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.7,
                top_p=0.95,
            )
            new_summary = response.choices[0].message.content
            conversation_data[chat_id]["summary"] = new_summary
        except Exception as e:
            criteria_logger.error(f"Error updating rolling summary for chat {chat_id}: {e}")


async def reply_with_perplexity(context: ContextTypes.DEFAULT_TYPE, update: Update, query: str) -> None:
    """
    Uses the Perplexity integration to get a detailed answer to `query`
    and sends that response to the user.
    """
    try:
        processing_msg = await update.message.reply_text("Analyzing request (auto-triggered by criteria)...")
        loop = asyncio.get_event_loop()
        reply_full = await loop.run_in_executor(None, get_perplexity_response, query)
        await processing_msg.delete()

        # Send the final answer as a simple text message
        await update.message.reply_text(reply_full)
    except Exception as e:
        criteria_logger.error(f"Error performing Perplexity search: {e}")
        await update.message.reply_text("An error occurred while performing the search.")
