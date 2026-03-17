"""Local Ollama LLM Client for Jarvis-Bud."""

import requests
import json
from typing import Optional, AsyncGenerator
import asyncio


class OllamaClient:
    """
    Client for interacting with local Ollama instances.
    Suitable for home/office use via naspi/pironman network.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        """Initialize Ollama client.
        
        Args:
            base_url: Ollama server URL (default localhost)
            model: Model to use (default mistral)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.is_available = False
        self._check_availability()

    def _check_availability(self) -> bool:
        """Check if Ollama server is available.
        
        Returns:
            True if server responds
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            self.is_available = response.status_code == 200
            if self.is_available:
                print(f"✅ Ollama available at {self.base_url}")
            else:
                print(f"⚠️  Ollama server not responding at {self.base_url}")
            return self.is_available
        except Exception as e:
            print(f"⚠️  Cannot reach Ollama at {self.base_url}: {e}")
            self.is_available = False
            return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Generate a response synchronously.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context
            
        Returns:
            Generated response or None if error
        """
        if not self.is_available:
            return None
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"❌ Ollama error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error calling Ollama: {e}")
            return None

    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate response with streaming (async).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Yields:
            Response chunks
        """
        if not self.is_available:
            return
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "temperature": 0.7
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Run blocking request in executor
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    stream=True,
                    timeout=30
                )
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            yield chunk.get("response", "")
                        except json.JSONDecodeError:
                            pass
                    await asyncio.sleep(0)  # Allow other tasks to run
            
        except Exception as e:
            print(f"❌ Error in async Ollama call: {e}")

    def list_models(self) -> list:
        """List available models on the Ollama server.
        
        Returns:
            List of model names
        """
        if not self.is_available:
            return []
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m.get("name") for m in models]
        except Exception as e:
            print(f"⚠️  Error listing models: {e}")
        
        return []

    def pull_model(self, model_name: str) -> bool:
        """Pull/download a model from Ollama library.
        
        Args:
            model_name: Model to download
            
        Returns:
            True if successful
        """
        if not self.is_available:
            return False
        
        try:
            print(f"📥 Pulling model {model_name}...")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=300
            )
            
            if response.status_code == 200:
                print(f"✅ Model {model_name} ready")
                return True
            else:
                print(f"❌ Failed to pull model: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error pulling model: {e}")
            return False

    def get_model_info(self) -> dict:
        """Get information about the current model.
        
        Returns:
            Model metadata
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": self.model},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"⚠️  Error getting model info: {e}")
        
        return {}
