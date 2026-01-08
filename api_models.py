"""
Dynamic AI Model Fetching

This module fetches available models from AI provider APIs.
Supports Google Gemini, OpenAI, and Anthropic.
"""

import httpx
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ModelFetcher:
    """Fetch available models from AI provider APIs."""

    @staticmethod
    async def fetch_google_models(api_key: Optional[str] = None) -> List[str]:
        """
        Fetch available Gemini models.

        Args:
            api_key: Google API key (optional for listing)

        Returns:
            List of model names
        """
        try:
            # Try to fetch from Google's API
            if api_key:
                import google.generativeai as genai
                genai.configure(api_key=api_key)

                # List all available models
                models = []
                for model in genai.list_models():
                    if 'generateContent' in model.supported_generation_methods:
                        # Extract model name
                        model_name = model.name.replace('models/', '')
                        models.append(model_name)

                if models:
                    return sorted(models)
        except Exception as e:
            logger.warning(f"Failed to fetch Google models from API: {e}")

        # Fallback to known models
        return [
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-thinking-exp-01-21",
            "gemini-exp-1206",
            "gemini-1.5-pro",
            "gemini-1.5-pro-002",
            "gemini-1.5-flash",
            "gemini-1.5-flash-002",
            "gemini-1.5-flash-8b",
        ]

    @staticmethod
    async def fetch_openai_models(api_key: Optional[str] = None) -> List[str]:
        """
        Fetch available OpenAI models.

        Args:
            api_key: OpenAI API key

        Returns:
            List of model names
        """
        if api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        # Filter for chat models
                        models = [
                            m["id"] for m in data.get("data", [])
                            if any(prefix in m["id"] for prefix in ["gpt-4", "gpt-3.5"])
                        ]
                        if models:
                            return sorted(models)
            except Exception as e:
                logger.warning(f"Failed to fetch OpenAI models from API: {e}")

        # Fallback to known models
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ]

    @staticmethod
    async def fetch_anthropic_models(api_key: Optional[str] = None) -> List[str]:
        """
        Fetch available Anthropic models.

        Note: Anthropic doesn't have a public models endpoint,
        so we return the known models.

        Args:
            api_key: Anthropic API key (unused)

        Returns:
            List of model names
        """
        # Anthropic doesn't expose a models list API
        # Return current models as of Jan 2026
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    @staticmethod
    async def fetch_all_models(
        provider: str,
        api_key: Optional[str] = None
    ) -> List[str]:
        """
        Fetch models for a specific provider.

        Args:
            provider: Provider name ('google', 'openai', 'anthropic')
            api_key: API key for the provider

        Returns:
            List of model names
        """
        provider = provider.lower()

        if provider == "google":
            return await ModelFetcher.fetch_google_models(api_key)
        elif provider == "openai":
            return await ModelFetcher.fetch_openai_models(api_key)
        elif provider == "anthropic":
            return await ModelFetcher.fetch_anthropic_models(api_key)
        else:
            return []


# Static fallback models (used when API fetch fails)
FALLBACK_MODELS: Dict[str, List[str]] = {
    "google": [
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ],
}


def get_fallback_models(provider: str) -> List[str]:
    """
    Get fallback models for a provider.

    Args:
        provider: Provider name

    Returns:
        List of model names
    """
    return FALLBACK_MODELS.get(provider.lower(), [])
