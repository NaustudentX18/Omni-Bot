"""Dual-Path AI Router for Jarvis-Bud."""

from collections.abc import AsyncGenerator

from .ollama_client import OllamaClient
from .openrouter_client import OpenRouterClient


class AIRouter:
    """
    Intelligent router that selects between local Ollama and cloud OpenRouter.
    Prioritizes local when available, falls back to cloud for better results.
    """

    def __init__(self, ollama_url: str | None = None, openrouter_key: str | None = None):
        """Initialize AI router with both backends.

        Args:
            ollama_url: Ollama server URL (auto-detect if None)
            openrouter_key: OpenRouter API key (can be added later)
        """
        # Initialize Ollama
        self.ollama = None
        if ollama_url:
            self.ollama = OllamaClient(base_url=ollama_url)
        else:
            # Try common local addresses
            for url in [
                "http://localhost:11434",
                "http://192.168.1.100:11434",
                "http://naspi:11434",
            ]:
                client = OllamaClient(base_url=url)
                if client.is_available:
                    self.ollama = client
                    break

        # Initialize OpenRouter
        self.openrouter = None
        if openrouter_key:
            self.openrouter = OpenRouterClient(api_key=openrouter_key)

    def set_openrouter_key(self, api_key: str) -> bool:
        """Add or update OpenRouter API key.

        Args:
            api_key: OpenRouter API key

        Returns:
            True if connection successful
        """
        self.openrouter = OpenRouterClient(api_key=api_key)
        return self.openrouter.is_available

    def get_route_info(self) -> dict:
        """Get information about available routes.

        Returns:
            Dict with route availability
        """
        return {
            "local_available": self.ollama is not None and self.ollama.is_available,
            "cloud_available": self.openrouter is not None and self.openrouter.is_available,
            "local_model": self.ollama.model if self.ollama else None,
            "cloud_model": self.openrouter.model if self.openrouter else None,
        }

    def generate(
        self, prompt: str, system_prompt: str | None = None, prefer: str = "local"
    ) -> str | None:
        """Generate response with smart routing.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            prefer: Route preference ("local", "cloud", "auto")

        Returns:
            Generated response or None
        """
        # Route selection logic
        if prefer == "local":
            # Try local first, fall back to cloud
            if self.ollama and self.ollama.is_available:
                print("🏠 Using local Ollama...")
                result = self.ollama.generate(prompt, system_prompt)
                if result:
                    return result

            if self.openrouter and self.openrouter.is_available:
                print("☁️  Falling back to OpenRouter...")
                return self.openrouter.generate(prompt, system_prompt)

        elif prefer == "cloud":
            # Try cloud first, fall back to local
            if self.openrouter and self.openrouter.is_available:
                print("☁️  Using OpenRouter...")
                result = self.openrouter.generate(prompt, system_prompt)
                if result:
                    return result

            if self.ollama and self.ollama.is_available:
                print("🏠 Falling back to local Ollama...")
                return self.ollama.generate(prompt, system_prompt)

        elif prefer == "auto":
            # Auto-select based on prompt size and availability
            prompt_tokens = len(prompt.split())

            # Use cloud for complex queries, local for simple ones
            if prompt_tokens > 100 and self.openrouter and self.openrouter.is_available:
                print("☁️  Using OpenRouter (complex query)...")
                result = self.openrouter.generate(prompt, system_prompt)
                if result:
                    return result

            if self.ollama and self.ollama.is_available:
                print("🏠 Using local Ollama...")
                return self.ollama.generate(prompt, system_prompt)

            if self.openrouter and self.openrouter.is_available:
                print("☁️  Using OpenRouter...")
                return self.openrouter.generate(prompt, system_prompt)

        print("❌ No AI routes available!")
        return None

    async def generate_async(
        self, prompt: str, system_prompt: str | None = None, prefer: str = "local"
    ) -> AsyncGenerator[str, None]:
        """Generate response with streaming and smart routing.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            prefer: Route preference ("local", "cloud", "auto")

        Yields:
            Response chunks
        """
        # Similar routing logic for async
        if prefer == "local":
            if self.ollama and self.ollama.is_available:
                print("🏠 Using local Ollama (async)...")
                async for chunk in self.ollama.generate_async(prompt, system_prompt):
                    yield chunk
                return

            if self.openrouter and self.openrouter.is_available:
                print("☁️  Falling back to OpenRouter (async)...")
                async for chunk in self.openrouter.generate_async(prompt, system_prompt):
                    yield chunk
                return

        elif prefer == "cloud":
            if self.openrouter and self.openrouter.is_available:
                print("☁️  Using OpenRouter (async)...")
                async for chunk in self.openrouter.generate_async(prompt, system_prompt):
                    yield chunk
                return

            if self.ollama and self.ollama.is_available:
                print("🏠 Local Ollama (async)...")
                async for chunk in self.ollama.generate_async(prompt, system_prompt):
                    yield chunk
                return

        elif prefer == "auto":
            if self.ollama and self.ollama.is_available:
                print("🏠 Using local Ollama (async)...")
                async for chunk in self.ollama.generate_async(prompt, system_prompt):
                    yield chunk
                return

            if self.openrouter and self.openrouter.is_available:
                print("☁️  Using OpenRouter (async)...")
                async for chunk in self.openrouter.generate_async(prompt, system_prompt):
                    yield chunk
                return

        print("❌ No AI routes available!")
