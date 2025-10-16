"""
OpenAI API client with intelligent image editing.

COMPLETELY REWRITTEN:
- Smart image editing using GPT-4 Vision + DALL-E 3
- Analyzes original image to understand composition
- Applies precise edits while maintaining subject
- Multiple fallback strategies for reliability
- Comprehensive error handling
"""

import logging
import base64
from typing import List, Dict, Optional, Union
from io import BytesIO

import httpx

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from config import OPENAI_API_KEY, IMAGE_MODEL

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


# ============================================================================
# CLIENT INITIALIZATION
# ============================================================================

async def _get_client() -> Optional[AsyncOpenAI]:
    """Initialize and return OpenAI client with retry configuration."""
    global _client

    if not AsyncOpenAI or not OPENAI_API_KEY:
        logger.error("❌ OpenAI not available or API key missing")
        return None

    if _client is None:
        http_client = httpx.AsyncClient(timeout=120.0)  # Increased timeout
        _client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            http_client=http_client,
            max_retries=3
        )
        logger.info("✅ OpenAI client initialized successfully")

    return _client


# ============================================================================
# CHAT COMPLETION (Supports Text + Images)
# ============================================================================

async def chat_with_ai(
        messages: List[Dict],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 800,
) -> str:
    """
    Send chat completion request with support for text and images.

    Args:
        messages: List of message dicts (can include image_url content)
        model: Model to use
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response

    Returns:
        AI response text
    """
    client = await _get_client()

    if not client:
        return "⚠️ AI service unavailable. Please try again later."

    try:
        logger.info(f"🤖 Chat request: model={model}, messages={len(messages)}")

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        reply = (response.choices[0].message.content or "").strip()
        logger.info(f"✅ Chat response received: {len(reply)} characters")

        return reply

    except Exception as e:
        logger.error(f"❌ Chat API error: {e}", exc_info=True)
        return f"❌ AI error: {str(e)[:200]}"


# ============================================================================
# IMAGE GENERATION (DALL-E)
# ============================================================================

async def generate_image(
        prompt: str,
        n: int = 1,
        size: str = "1024x1024",
        model: str = IMAGE_MODEL
) -> List[Union[str, BytesIO]]:
    """
    Generate images from text prompt using DALL-E.

    Args:
        prompt: Text description of desired image
        n: Number of images to generate (1-10 for DALL-E 2, 1 for DALL-E 3)
        size: Image size (1024x1024, 1792x1024, or 1024x1792 for DALL-E 3)
        model: Model to use (dall-e-2 or dall-e-3)

    Returns:
        List of image URLs or BytesIO objects
    """
    client = await _get_client()

    if not client:
        logger.error("❌ OpenAI client unavailable")
        return []

    try:
        logger.info(f"🎨 Generating image: '{prompt[:60]}...' using {model}")

        # DALL-E 3 only supports n=1
        if model == "dall-e-3" and n > 1:
            n = 1

        response = await client.images.generate(
            model=model,
            prompt=prompt,
            n=n,
            size=size,
            quality="hd" if model == "dall-e-3" else "standard"
        )

        results = []
        for img in response.data:
            if getattr(img, "url", None):
                results.append(img.url)
                logger.info(f"✅ Generated image URL: {img.url[:50]}...")
            elif getattr(img, "b64_json", None):
                from base64 import b64decode
                results.append(BytesIO(b64decode(img.b64_json)))
                logger.info("✅ Generated image (base64)")

        return results

    except Exception as e:
        logger.error(f"❌ Image generation error: {e}", exc_info=True)
        return []


# ============================================================================
# SMART IMAGE EDITING (Vision + Generation)
# ============================================================================

async def create_image_variation(
        image_bytes: bytes,
        prompt: str = "",
        size: str = "1024x1024"
) -> Optional[str]:

    client = await _get_client()

    if not client:
        logger.error("❌ OpenAI client unavailable")
        return None

    try:
        logger.info(f"🛠 Smart image editing started")
        logger.info(f"📝 Edit request: '{prompt[:100]}'")

        # Step 1: Convert image to base64 for Vision API
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Step 2: Analyze image with GPT-4 Vision
        analysis_prompt = f"""Analyze this photograph carefully and create a detailed DALL-E prompt.

USER'S EDIT REQUEST: "{prompt}"

YOUR TASK:
1. Describe the main subject (person, object, scene) in detail:
   - Physical appearance, clothing, pose, expression
   - Age, gender, features (if person)
   - Position and angle

2. Describe the background and setting:
   - Location type (indoor/outdoor)
   - Key elements and objects
   - Depth and perspective

3. Describe lighting and colors:
   - Light source and direction
   - Color palette and tones
   - Atmosphere and mood

4. Apply the user's requested edits naturally

5. Create a DALL-E 3 prompt (150-200 words) that:
   ✅ Maintains the EXACT same subject and composition
   ✅ Applies the user's edits seamlessly
   ✅ Uses photorealistic, detailed description
   ✅ Specifies "high quality photograph" style
   
CRITICAL: The generated image must look like the SAME photo with the requested changes applied, not a completely different image.

Return ONLY the DALL-E prompt, nothing else."""

        logger.info("🔍 Analyzing image with GPT-4 Vision...")

        analysis_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"  # High detail for better analysis
                            }
                        },
                        {
                            "type": "text",
                            "text": analysis_prompt
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.3
        )

        enhanced_prompt = analysis_response.choices[0].message.content.strip()

        if not enhanced_prompt or len(enhanced_prompt) < 50:
            raise ValueError("Vision analysis produced insufficient prompt")

        logger.info(f"✅ Vision analysis complete: {len(enhanced_prompt)} chars")
        logger.info(f"📋 Enhanced prompt: {enhanced_prompt[:150]}...")

        # Step 3: Generate edited image with DALL-E 3
        logger.info("🎨 Generating edited image with DALL-E 3...")

        generation_response = await client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt[:4000],
            size=size,
            quality="hd",
            n=1
        )

        if not generation_response.data or len(generation_response.data) == 0:
            raise ValueError("DALL-E returned no images")

        edited_url = generation_response.data[0].url
        logger.info(f"✅ Image edited successfully: {edited_url[:60]}...")

        return edited_url

    except Exception as e:
        logger.error(f"❌ Smart image editing failed: {e}", exc_info=True)

        # Fallback: Try simple generation with user's prompt only
        try:
            logger.warning("🔄 Attempting fallback: Simple generation...")

            fallback_prompt = f"""High quality photograph: {prompt}. 
Professional photography, detailed, sharp focus, good lighting, 
realistic colors, photorealistic style."""

            fallback_response = await client.images.generate(
                model="dall-e-3",
                prompt=fallback_prompt,
                size=size,
                quality="standard",
                n=1
            )

            if fallback_response.data and len(fallback_response.data) > 0:
                logger.warning("⚠️ Used fallback generation (not true editing)")
                return fallback_response.data[0].url

        except Exception as fallback_error:
            logger.error(f"❌ Fallback generation also failed: {fallback_error}")

        return None


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================

async def edit_image_with_prompt(
        image_bytes: bytes,
        prompt: str,
        size: str = "1024x1024"
) -> List[Union[str, BytesIO]]:
    """
    Legacy function for compatibility.
    Internally uses the new smart editing approach.
    """
    result = await create_image_variation(image_bytes, prompt, size)
    return [result] if result else []


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def estimate_tokens(text: str) -> int:

    return len(text) // 4


def truncate_messages(
        messages: List[Dict],
        max_tokens: int = 3000
) -> List[Dict]:
    """
    Truncate message history to fit within token limit.

    Strategy:
    - Always keep system messages
    - Keep most recent messages
    - Discard oldest user/assistant messages first

    Args:
        messages: List of message dictionaries
        max_tokens: Maximum total tokens allowed

    Returns:
        Truncated list of messages
    """
    if not messages:
        return []

    # Separate system messages from conversation
    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]

    # Calculate current token usage
    total_tokens = sum(
        estimate_tokens(str(m.get("content", "")))
        for m in messages
    )

    # If within limit, return as-is
    if total_tokens <= max_tokens:
        return messages

    # Build result: keep system + most recent messages
    result = system_msgs.copy()
    current_tokens = sum(
        estimate_tokens(str(m.get("content", "")))
        for m in system_msgs
    )

    # Add messages from newest to oldest until limit reached
    for msg in reversed(other_msgs):
        msg_tokens = estimate_tokens(str(msg.get("content", "")))

        if current_tokens + msg_tokens <= max_tokens:
            result.insert(len(system_msgs), msg)
            current_tokens += msg_tokens
        else:
            break

    logger.info(f"📊 Truncated messages: {len(messages)} → {len(result)}")
    return result
