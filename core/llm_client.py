"""Ollama LLM client - 100% FREE local AI"""

import ollama
from typing import Generator, Optional, Dict, List


class OllamaClient:
    """Client for interacting with local Ollama LLM"""
    
    def __init__(self, model_name: str = "llama3.2:latest", temperature: float = 0.7):
        """
        Initialize Ollama client
        
        Args:
            model_name: Name of the Ollama model to use
            temperature: Generation temperature (0.0 - 1.0)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.available = self._check_availability()
        
        if self.available:
            print(f"[OllamaClient] ✅ Connected to Ollama with model: {model_name}")
        else:
            print(f"[OllamaClient] ⚠️ Ollama not available or model not found")


    # Modify from here
    """Enhanced _check_availability with better error messages"""

    def _check_availability(self) -> bool:
        """Check if Ollama is available and model is installed"""
        try:
            # Try to list models
            try:
                models = ollama.list()
            except ollama.ResponseError as e:
                # This often happens if Ollama is running but no models are pulled
                print(f"[OllamaClient] ❌ Ollama Response Error: {e}")
                return False
            except ConnectionError as e:
                # This is the critical case where the service is not running or unreachable
                print(f"[OllamaClient] ❌ Cannot connect to Ollama service! ConnectionError: {e}")
                print(f"[OllamaClient] ")
                print(f"[OllamaClient] Is Ollama running?")
                print(f"[OllamaClient]   Windows: Check system tray or run 'ollama serve'")
                print(f"[OllamaClient]   Mac/Linux: Run 'ollama serve &' or 'systemctl start ollama'")
                print(f"[OllamaClient] ")
                print(f"[OllamaClient] Or install Ollama from: https://ollama.com/download")
                return False
            
            # The ollama library returns a dictionary with a 'models' key.
            # We assume a successful connection returns a dict.
            model_list = models.get('models', [])
            
            # Extract model names safely
            model_names = []
            for m in model_list:
                if isinstance(m, dict):
                    # The model name is under the 'name' key
                    name = m.get('name')
                    if name:
                        model_names.append(name)
            
            # Check if any models exist
            if not model_names:
                print(f"[OllamaClient] ❌ No models installed!")
                print(f"[OllamaClient] Install a model with:")
                print(f"[OllamaClient]   ollama pull {self.model_name}")
                print(f"[OllamaClient] ")
                print(f"[OllamaClient] Popular alternatives:")
                print(f"[OllamaClient]   ollama pull llama3.2:1b     # Smaller/faster")
                print(f"[OllamaClient]   ollama pull llama3.1        # Alternative")
                print(f"[OllamaClient]   ollama pull mistral         # Another option")
                return False
            
            # Check for model match
            model_available = False
            matched_model = None
            
            for available_model in model_names:
                # Check exact match (e.g., "llama3.2:latest" == "llama3.2:latest")
                if available_model == self.model_name:
                    model_available = True
                    matched_model = available_model
                    break
                # Check if base name matches (e.g., "llama3.2:latest" matches "llama3.2")
                if available_model.startswith(self.model_name.split(':')[0] + ":"):
                    model_available = True
                    matched_model = available_model
                    self.model_name = available_model
                    break
            
            if model_available and matched_model:
                print(f"[OllamaClient] ✅ Found model: {matched_model}")
                return True
            
            # Model not found but others exist
            print(f"[OllamaClient] ❌ Model '{self.model_name}' not found")
            print(f"[OllamaClient] ")
            print(f"[OllamaClient] Available models on your system:")
            for model in model_names:
                print(f"[OllamaClient]   - {model}")
            print(f"[OllamaClient] ")
            print(f"[OllamaClient] Install '{self.model_name}' with:")
            print(f"[OllamaClient]   ollama pull {self.model_name}")
            
            return False
            

            
        except Exception as e:
            print(f"[OllamaClient] ❌ Error checking Ollama: {e}")
            print(f"[OllamaClient] ")
            print(f"[OllamaClient] Troubleshooting:")
            print(f"[OllamaClient]   1. Verify Ollama is installed: ollama --version")
            print(f"[OllamaClient]   2. Check if service is running: ollama list")
            print(f"[OllamaClient]   3. Restart Ollama service")
            print(f"[OllamaClient]   4. Install from: https://ollama.com/download")
            return False

    # End of modifyments

    
    def is_available(self) -> bool:
        """Check if client is ready to use"""
        return self.available
    
    def list_models(self) -> List[str]:
        """Get list of available models"""
        try:
            models = ollama.list()
            
            # The ollama library returns a dictionary with a 'models' key.
            # We assume a successful connection returns a dict.
            model_list = models.get('models', [])
            
            # Extract model names safely
            model_names = []
            for m in model_list:
                if isinstance(m, dict):
                    # The model name is under the 'name' key
                    name = m.get('name')
                    if name:
                        model_names.append(name)
            
            return model_names
        except Exception as e:
            print(f"[OllamaClient] Error listing models: {e}")
            return []
    
    def generate(self, prompt: str, stream: bool = False, 
                max_tokens: int = 2000) -> str:
        """
        Generate response from LLM
        
        Args:
            prompt: Input prompt
            stream: Whether to stream response
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        if not self.available:
            return "Error: Ollama not available. Please install Ollama and pull a model."
        
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                stream=stream,
                options={
                    'temperature': self.temperature,
                    'num_predict': max_tokens
                }
            )
            
            if stream:
                return response  # Return generator for streaming
            else:
                return response['response']
                
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(f"[OllamaClient] {error_msg}")
            return error_msg
    
    def stream_generate(self, prompt: str, max_tokens: int = 2000) -> Generator[str, None, None]:
        """
        Stream response from LLM
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Yields:
            Text chunks as they're generated
        """
        if not self.available:
            yield "Error: Ollama not available. Please install Ollama and pull a model."
            return
        
        try:
            stream = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                stream=True,
                options={
                    'temperature': self.temperature,
                    'num_predict': max_tokens
                }
            )
            
            for chunk in stream:
                if 'response' in chunk:
                    yield chunk['response']
                    
        except Exception as e:
            error_msg = f"Error streaming response: {str(e)}"
            print(f"[OllamaClient] {error_msg}")
            yield error_msg
    
    def set_model(self, model_name: str) -> bool:
        """
        Change the active model
        
        Args:
            model_name: New model name
            
        Returns:
            True if successful
        """
        old_model = self.model_name
        self.model_name = model_name
        self.available = self._check_availability()
        
        if self.available:
            print(f"[OllamaClient] Switched to model: {model_name}")
            return True
        else:
            self.model_name = old_model
            self.available = self._check_availability()
            print(f"[OllamaClient] Failed to switch to {model_name}, staying with {old_model}")
            return False
    
    def set_temperature(self, temperature: float):
        """Set generation temperature"""
        self.temperature = max(0.0, min(1.0, temperature))
        print(f"[OllamaClient] Temperature set to {self.temperature}")