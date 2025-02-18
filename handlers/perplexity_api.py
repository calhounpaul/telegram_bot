import logging
from openai import OpenAI
import os

PX_API_KEY_FILE = "secrets/perplexity_api_key.txt"
PX_ENDPOINT_URL = "https://api.perplexity.ai"

with open(PX_API_KEY_FILE, "r") as f:
    PX_API_KEY = f.read().strip()

PPX_QUERY_PREPROMPT = ""

if "research_prefix_personality.txt" in os.listdir("secrets"):
    with open("secrets/research_prefix_personality.txt", "r") as f:
        PPX_QUERY_PREPROMPT = f.read().strip()

px_client = OpenAI(base_url=PX_ENDPOINT_URL, api_key=PX_API_KEY)

def get_perplexity_response(query: str, preprompt: str = PPX_QUERY_PREPROMPT) -> str:
    """
    Generate a response from the Perplexity API given a query.
    """
    try:
        response = px_client.chat.completions.create(
            model="sonar-pro",  # Replace with your preferred model if needed
            messages=[{"role": "user", "content": PPX_QUERY_PREPROMPT + query}],
            max_tokens=2048,
            temperature=0.7,
            top_p=0.95,
        )
        reply = response.choices[0].message.content
        citations = ""
        if response.citations:
            citations = "\n\n" + "\n".join([str(n+1) +". " + response.citations[n] for n in range(len(response.citations)) if "[" + str(n+1) + "]" in reply])
        reply += citations
    except Exception as e:
        logging.error(f"Error generating Perplexity response: {e}")
        reply = "An error occurred while generating the response."
    return reply
