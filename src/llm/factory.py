import os
from dotenv import load_dotenv

# Importiamo il client locale che abbiamo appena scritto
from src.llm.slm_client import SLMClient
from src.llm.github_client import LLMClient
from src.llm.gemini_client import GeminiClient

# Carica le variabili dal file .env
load_dotenv()

class LLMFactory:
    @staticmethod
    def get_client():
        """
        Legge il file .env e restituisce il client corretto già configurato.
        """
        # Legge il provider (se non trova nulla nel .env, usa 'local' di default)
        provider = os.getenv("LLM_PROVIDER", "local").lower()

        if provider == "local":
            # Legge le variabili specifiche di Ollama che hai nel tuo .env
            model_name = os.getenv("OLLAMA_MODEL", "novaforgeai/qwen2.5-3b:q4km")
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            # Restituisce il client locale pronto all'uso
            return SLMClient(model_name=model_name, base_url=base_url)
        
        elif provider == "github":
            print("[Factory] Attivazione modulo GitHub...")
            model_name = os.getenv("GITHUB_MODEL", "gpt-4o")
            base_url = os.getenv(
                "GITHUB_BASE_URL",
                "https://models.inference.ai.azure.com",
            )
            api_key = os.getenv("GITHUB_TOKEN", "")

            return LLMClient(
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
            )
        
        elif provider == "gemini":
            print("[Factory] Attivazione modulo Google Gemini...")
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            base_url = os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/",
            )
            api_key = os.getenv("GEMINI_API_KEY", "")

            return GeminiClient(
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
            )
        else:
            raise ValueError(f"LLM_PROVIDER non riconosciuto nel file .env: {provider}")