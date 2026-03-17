"""OpenRouter Cloud LLM Client for Jarvis-Bud."""

import requests
import json
from typing import Optional, AsyncGenerator
import asyncio


class OpenRouterClient:
    """
    Client for OpenRouter cloud LLM service.
    Supports Gemini 2.0 Flash Lite, Llama 3.3, and other models.
    Suitable for mobile/outdoor use.
    """

    # Recommended free models on OpenRouter
    DEFAULT_MODELS = {
        "gemini": "google/gemini-2.0-flash-lite:free",
        "llama": "meta-llama/llama-3.3-70b-instruct:free",
        "mixtral": "mistralai/mixtral-8x7b-instruct:free"
    }

    def __init__(self, api_key: str, model: str = "gemini"):
        """Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            model: Model preset ("gemini", "llama", "mixtral") or full model ID
        """
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        
        # Resolve model ID
        if model in self.DEFAULT_MODELS:
            self.model = self.DEFAULT_MODELS[model]
        else:
            self.model = model
        
        self.is_available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if OpenRouter API is accessible.
        
        Returns:
            True if API responds
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ OpenRouter available (API key valid)")
                return True
            else:
                print(f"⚠️  OpenRouter API error: {response.status_code}")
                print(f"    Response: {response.text[:100]}")
                return False
                
        except Exception as e:
            print(f"⚠️  Cannot reach OpenRouter: {e}")
            return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Generate a response synchronously.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Generated response or None if error
        """
        if not self.is_available:
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 500
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("choices") and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"❌ OpenRouter error: {response.status_code}")
                print(f"    {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Error calling OpenRouter: {e}")
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "stream": True,
                "max_tokens": 500
            }
            
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=30
                )
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    try:
                        line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                        
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str == "[DONE]":
                                break
                            
                            chunk = json.loads(data_str)
                            if chunk.get("choices") and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                    except (json.JSONDecodeError, AttributeError):
                        pass
                    
                    await asyncio.sleep(0)  # Allow other tasks
            
        except Exception as e:
            print(f"❌ Error in async OpenRouter call: {e}")

    def list_free_models(self) -> list:
        """List available free models on OpenRouter.
        
        Returns:
            List of model names
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get("data", [])
                free_models = [
                    m.get("id")
                    for m in models
                    if ":free" in m.get("id", "")
                ]
                return free_models
                
        except Exception as e:
            print(f"⚠️  Error listing models: {e}")
        
        return list(self.DEFAULT_MODELS.values())

    def get_model_info(self) -> dict:
        """Get information about current model.
        
        Returns:
            Model metadata
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get("data", [])
                for model in models:
                    if model.get("id") == self.model:
                        return model
                
        except Exception as e:
            print(f"⚠️  Error getting model info: {e}")
        
        return {}
