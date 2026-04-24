"""Unified LLM utility wrapper using litellm."""

import json

import litellm

from backend.config import get_settings


async def llm_call(
    prompt: str,
    system: str = "",
    model: str = None,
    response_format: dict = None,
    images: list = None,
) -> str:
    """Unified LLM call via litellm. Returns the text response."""
    cfg = get_settings()
    model = model or cfg.llm_model
    messages = []

    if system:
        messages.append({"role": "system", "content": system})

    if images:
        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}
            )
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})

    kwargs = {"model": model, "messages": messages}
    if response_format:
        kwargs["response_format"] = response_format
    if cfg.litellm_api_base:
        kwargs["api_base"] = cfg.litellm_api_base
    if cfg.litellm_api_key:
        kwargs["api_key"] = cfg.litellm_api_key

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content


def parse_json_response(text: str) -> dict | list:
    """Extract JSON from LLM response, handling markdown code blocks.

    Args:
        text: Raw LLM response text that may contain JSON wrapped
              in markdown code fences.

    Returns:
        Parsed JSON as a dict or list.

    Raises:
        json.JSONDecodeError: If the text does not contain valid JSON.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)
