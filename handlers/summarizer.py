import logging
from typing import List
from openai import OpenAI

# Load the Hyperbolic API key from file.
#HYPERBOLIC_API_KEY_FILE = "secrets/hyperbolic_api_key.txt"
#HYPERBOLIC_ENDPOINT = "https://api.hyperbolic.xyz/v1"
API_KEY_FILE = "secrets/hf_api_key.txt"
ENDPOINT = "https://api-inference.huggingface.co/v1/"
MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct"

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
    chat_text = "\n".join(chat_messages)
    
    # Build the prompt with the required instructions.
    prompt = (
        f"summarize the following chat:\nCHAT_BEGIN{chat_text}\nCHAT_END\n"
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
