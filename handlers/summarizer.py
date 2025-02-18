import logging
from typing import List
from openai import OpenAI

# Load the Hyperbolic API key from file.
API_KEY_FILE = "secrets/hyperbolic_api_key.txt"
ENDPOINT = "https://api.hyperbolic.xyz/v1/"
#API_KEY_FILE = "secrets/hf_api_key.txt"
#ENDPOINT = "https://api-inference.huggingface.co/v1/"
MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct"
MAX_CHARS = 100*(10**3)*4
MSG_SEPARATOR = "\n---New Message---\n"

with open(API_KEY_FILE, "r") as f:
    HYPERBOLIC_API_KEY = f.read().strip()

# Create a client for the Llama 3.3-70B-Instruct model via Hyperbolic.
llama_client = OpenAI(base_url=ENDPOINT, api_key=HYPERBOLIC_API_KEY)

def summarize_chat(chat_messages: List[str]) -> str:
    """
    Summarizes a chat by concatenating messages from different users
    and instructing the Llama 3.3-70B-Instruct model to produce a summary.
    
    The prompt instructs the model:
      "summarize the following chat: <all messages concatenated> your summary should be no larger than two paragraphs of 4 sentences each."
    
    Parameters:
        chat_messages (List[str]): A list of chat messages from different users.
        
    Returns:
        str: The generated summary, or an error message if something goes wrong.
    """
    # Concatenate all messages into a single block of text.
    chat_text = MSG_SEPARATOR.join(chat_messages)[-MAX_CHARS:]
    
    # Build the prompt with the required instructions.
    prompt = (
        f"Summarize the following chat:\n####CHAT_BEGIN####{chat_text}\n####CHAT_END####\n"
        "Your summary should be no larger than two paragraphs of 4 sentences each."
    )
    
    try:
        response = llama_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,       # Adjust as needed based on expected summary length.
            temperature=0.7,
            top_p=0.95,
        )
        summary = response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error in summarizing chat: {e}")
        summary = "An error occurred while summarizing the chat."
    
    return summary

def summarize_research(research_text: str) -> str:
    """
    Summarizes a /research return by instructing the LLM to produce a summary.
    """
    # Build the prompt with the required instructions.
    prompt = (
        f"Summarize the following information:\n####RESEARCH_BEGIN####{research_text}\n####RESEARCH_END####\n"
        "Your summary should be no larger than one paragraph of 3 sentences."
    )
    
    try:
        response = llama_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,       # Adjust as needed based on expected summary length.
            temperature=0.7,
            top_p=0.95,
        )
        summary = response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error in summarizing research: {e}")
        summary = "An error occurred while summarizing the research."
    
    return summary

# Example usage:
if __name__ == "__main__":
    # Example chat messages from different users.
    chat_logs = [
        "Alice: Hey, did anyone check out the new update?",
        "Bob: Yes, I tried it this morning and it seems promising.",
        "Charlie: I encountered some issues during installation.",
        "Alice: What kind of issues did you face?",
        "Charlie: Mainly compatibility problems with the old plugins.",
    ]
    
    summary = summarize_chat(chat_logs)
    print(summary)