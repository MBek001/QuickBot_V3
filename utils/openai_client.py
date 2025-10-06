"""
Asynchronous wrappers around the OpenAI API.

This module provides modern, async-compatible functions for:
 - Chat completions (GPT-4o, GPT-4o-mini)
 - Image generation (DALL·E via gpt-image-1)
 - Image analysis (Vision via GPT-4o)

It uses the modern `openai` SDK (v1.0+).
If the library or API key is missing, the functions gracefully return
friendly error messages instead of raising exceptions.
"""

import asyncio
from typing import List, Dict, Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from config import OPENAI_API_KEY


# Global client (lazy-loaded)
_client: Optional[AsyncOpenAI] = None


# ---------------------------------------------------------------------
# 🔧 Initialize OpenAI client
# ---------------------------------------------------------------------
async def _get_client() -> Optional[AsyncOpenAI]:
    """Return an AsyncOpenAI client instance if possible."""
    global _client
    if not AsyncOpenAI or not OPENAI_API_KEY:
        return None
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


# ---------------------------------------------------------------------
# 💬 Chat with AI
# ---------------------------------------------------------------------
async def chat_with_ai(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
) -> str:
    """
    Send a list of messages to OpenAI chat completion API.

    Parameters
    ----------
    messages : list[dict]
        Each dict should have {"role": "user"|"assistant"|"system", "content": "..."}.
    model : str
        Chat model to use. Defaults to 'gpt-4o-mini'.
    temperature : float
        Sampling temperature for creativity (0.0–1.0).

    Returns
    -------
    str : Assistant reply, or error message.
    """
    client = await _get_client()
    if not client:
        return "⚠️ AI service unavailable. Please contact the administrator."

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Chat error: {e}"


# ---------------------------------------------------------------------
# 🖼️ Generate Images
# ---------------------------------------------------------------------
async def generate_image(
    prompt: str,
    n: int = 1,
    size: str = "1024x1024",
) -> List[str]:
    """
    Generate one or more images from text using OpenAI's DALL·E model.

    Returns a list of image URLs (for Telegram you can directly send them).
    """
    client = await _get_client()
    if not client:
        return []

    try:
        response = await client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            n=n,
            size=size,
        )
        # Extract URLs
        urls = [getattr(img, "url", None) for img in response.data if getattr(img, "url", None)]
        return urls
    except Exception as e:
        print("Image generation error:", e)
        return []


# ---------------------------------------------------------------------
# 👁️ Analyze Images (Vision)
# ---------------------------------------------------------------------
async def analyze_image(
    image_url: str,
    prompt: Optional[str] = None,
) -> str:
    """
    Analyze or describe an image using GPT-4o's vision capabilities.

    Parameters
    ----------
    image_url : str
        A public or Telegram CDN URL of the image.
    prompt : str | None
        Additional context or question about the image.
    """
    client = await _get_client()
    if not client:
        return "⚠️ AI service unavailable. Please contact the administrator."

    try:
        messages = [
            {"role": "system", "content": "You are an AI assistant that describes and analyzes images."},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt or "Describe the image in detail."},
                    {"type": "input_image", "image_url": image_url},
                ],
            },
        ]
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_output_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Vision error: {e}"
