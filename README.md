# Telegram Bot - Multi-Functional Assistant

This Telegram bot is a versatile assistant that provides various functionalities, including art generation, chat summarization, and query responses using advanced AI models. It is built using the `python-telegram-bot` library and integrates with multiple APIs to deliver its features.

---

## Features

### 1. **Art Generation**
   - **Command**: `/art <prompt>`
   - **Description**: Generates art based on a text prompt using the Hyperbolic API.
   - **Example**: `/art sunset over mountains`
   - **Output**: Sends the generated image back to the user with the prompt as the caption.

### 2. **Chat Summarization**
   - **Command**: `/summarize [hours]`
   - **Description**: Summarizes the chat history of the past specified hours (default: 3 hours).
   - **Example**: `/summarize 4`
   - **Output**: Provides a concise summary of the chat messages in the specified time frame.

### 3. **Query Responses**
   - **Command**: `/research <query>`
   - **Description**: Answers user queries using the Perplexity API.
   - **Example**: `/research What is the capital of France?`
   - **Output**: Sends a summary of the research along with a txt file containing a detailed response to the query with citations.

### 4. **Message Logging**
   - **Description**: Logs all messages' text in a SQLite database for future reference and analysis. Attachments will be added soon.
   - **Logs**: Messages are stored with details such as message ID, chat ID, user ID, username, message type, content, and timestamp.

### 5. **Authorization**
   - **Description**: Restricts bot usage to authorized users and groups.

---

## Setup Instructions

### Prerequisites
1. **Python 3.8+**: Ensure Python is installed on your system.
2. **Telegram Bot Token**: Create a bot using [BotFather](https://core.telegram.org/bots#botfather) and obtain the API token.
3. **API Keys**:
   - **Hyperbolic API Key**: For art generation.
   - **Perplexity API Key**: For research responses.
   - **Hugging Face API Key**: For chat summarization.

### Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/calhounpaul/telegram_bot
   cd telegram-bot
   ```

2. **Set Up Secrets**:
   - Create a `secrets` directory in the root of the project:
     ```bash
     mkdir secrets
     ```
   - Add the following files with your API keys:
     - `secrets/telegram_api_key.txt`: Paste your Telegram bot token here.
     - `secrets/hyperbolic_api_key.txt`: Paste your Hyperbolic API key here.
     - `secrets/perplexity_api_key.txt`: Paste your Perplexity API key here.
     - `secrets/hf_api_key.txt`: Paste your Hugging Face API key here.
   - Add a `secrets/pre_whitelisted_users.txt` file with a list of usernames (one per line) that are pre-authorized to use the bot.
   - The bot will use a `secrets/whitelist.json` file to manage newly authorized users and groups:
     ```json
     {
       "users": ["user_id_1", "user_id_2"],
       "groups": ["group_id_1", "group_id_2"]
     }
     ```
   - Optionally, use `secrets/research_prefix_personality.txt` to add a prefix to each Perplexity.ai query.

3. 
   **Run the Bot in Tmux**:
   ```bash
   bash run.sh
   ```
   **Or Install it as a Service**:
   ```bash
   bash run.sh --keepalive
   ```
   **Uninstall With**:
   ```bash
   bash run.sh --uninstall
   ```

---

## File Structure

```
telegram-bot/
├── bot.py                     # Main bot script
├── handlers/                  # Handlers for different functionalities
│   ├── __init__.py
│   ├── art_generator.py       # Art generation logic
│   ├── message_handler.py     # Message handling and database management
│   ├── perplexity_api.py      # Perplexity API integration
│   ├── setup_logging.py       # Logging configuration
│   └── summarizer.py          # Chat summarization logic
├── secrets/                   # Directory for API keys and whitelists
│   ├── telegram_api_key.txt
│   ├── hyperbolic_api_key.txt
│   ├── perplexity_api_key.txt
│   ├── hf_api_key.txt
│   ├── pre_whitelisted_users.txt
│   ├── telegram_messages.db
│   ├── research_prefix_personality.txt
│   └── whitelist.json
├── logs/                      # Logs directory (created automatically)
│   ├── errors.log
│   ├── events.log
│   ├── messages.log           # Logs of all messages
