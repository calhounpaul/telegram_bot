import requests
import logging
import base64
import json
from typing import Optional

# Initialize logger
art_logger = logging.getLogger('art_logger')

with open("secrets/hyperbolic_api_key.txt", "r") as f:
    HYPERBOLIC_API_KEY = f.read().strip()

def generate_art(prompt: str) -> Optional[bytes]:
    """
    Generate art using the Hyperbolic API.
    
    Args:
        prompt (str): The prompt for art generation
        
    Returns:
        Optional[bytes]: The generated image as bytes, or None if generation failed
    """
    print("Generating art...")
    try:
        url = "https://api.hyperbolic.xyz/v1/image/generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {HYPERBOLIC_API_KEY}"
        }
        data = {
            "model_name": "FLUX.1-dev",
            "prompt": prompt,
            "steps": 30,
            "cfg_scale": 5,
            "enable_refiner": False,
            "height": 1024,
            "width": 1024,
            "backend": "auto"
        }
        
        art_logger.info(f"Generating art with prompt: {prompt[:100]}...")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        if 'image' in result.get('images', [{}])[0]:
            # Get base64 image data
            image_data = result['images'][0]['image']
            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_data)
            art_logger.info("Art generation successful")
            return image_bytes
        else:
            art_logger.error(f"No image data in response: {result}")
            return None
            
    except Exception as e:
        e = str(e)[:1000]
        art_logger.error(f"Error generating art: {e}")
        return None