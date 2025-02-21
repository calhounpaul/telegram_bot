# Telegram Bot - Multi-Functional Assistant

This Telegram bot is a versatile assistant that provides various functionalities, including art generation, chat summarization, and query responses using advanced AI models. It is built using the `python-telegram-bot` library and integrates with multiple APIs to deliver its features.

## Features

### 1. Art Generation

- **Command**: `/art <prompt>`
- **Description**: Generates art based on a text prompt using the Hyperbolic API.
- **Example**: `/art sunset over mountains`
- **Output**: Sends the generated image back to the user with the prompt as the caption.

### 2. Chat Summarization

- **Command**: `/summarize [hours]`
- **Description**: Summarizes the chat history of the past specified hours (default: 3 hours).
- **Example**: `/summarize 4`
- **Output**: Provides a concise summary of the chat messages in the specified time frame.

### 3. Query Responses

- **Command**: `/research <query>`
- **Description**: Answers user queries using the Perplexity API.
- **Example**: `/research What is the capital of France?`
- **Output**: Sends a summary of the research along with a `.txt` file containing a detailed response to the query with citations.

### 4. Message Logging

- **Description**: Logs all messages' text in a SQLite database for future reference and analysis. Attachments will be added soon.
- **Logs**: Messages are stored with details such as message ID, chat ID, user ID, username, message type, content, and timestamp.

### 5. Authorization

- **Description**: Restricts bot usage to authorized users and groups.

## Setup Instructions

### Prerequisites

- **Python 3.8+**: Ensure Python is installed on your system.
- **Telegram Bot Token**: Create a bot using BotFather and obtain the API token.
- **API Keys**:
  - **Hyperbolic API Key**: For art generation.
  - **Perplexity API Key**: For research responses.
  - **Hugging Face API Key**: For chat summarization.

### Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/calhounpaul/telegram_bot
   cd telegram_bot
   ```

2. **Set Up Environment Variables**:

   - Copy the `.env.example` file to `.env`:

     ```bash
     cp .env.example .env
     ```

   - Open the `.env` file and fill in the required API keys and configuration values:

     ```plaintext
     TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
     HF_API_KEY="your_hugging_face_api_key"
     HYPERBOLIC_API_KEY="your_hyperbolic_api_key"
     PERPLEXITY_API_KEY="your_perplexity_api_key"
     ```

3. **Run the Bot**:

   - **Run the Bot in Tmux**:

     ```bash
     bash run.sh
     ```

   - **Install it as a Service** (for persistent operation):

     ```bash
     bash run.sh --keepalive
     ```

4. **Uninstall the Bot**:

   ```bash
   bash run.sh --uninstall
   ```

## File Structure

```
telegram_bot/
├── bot.py                     # Main bot script
├── handlers/                  # Handlers for different functionalities
│   ├── __init__.py
│   ├── art_generator.py       # Art generation logic
│   ├── message_handler.py     # Message handling and database management
│   ├── perplexity_api.py      # Perplexity API integration
│   ├── setup_logging.py       # Logging configuration
│   └── summarizer.py          # Chat summarization logic
├── .env                       # Environment variables for API keys and configuration
├── .env.example               # Example environment variables file
├── requirements.txt           # Python dependencies
├── run.sh                     # Script to run or install the bot
├── logs/                      # Logs directory (created automatically)
│   ├── errors.log
│   ├── events.log
│   ├── messages.log           # Logs of all messages
└── README.md                  # This file
```