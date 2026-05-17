import os
from dotenv import load_dotenv

# Importiamo il client locale che abbiamo appena scritto
from src.llm.slm_client import SLMClient
# (L'import del cloud lo lasciamo commentato finché il tuo collega non lo implementerà)
# from src.llm.llm_clients import LLMClient 

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
        
        elif provider == "cloud":
            # Questa parte sarà gestita dalla Card 5 del tuo collega
            print("[Factory] Attivazione modulo Cloud...")
            raise NotImplementedError(
                "Il client Cloud (Card 5) non è ancora stato implementato dal tuo collega."
            )
        
        else:
            raise ValueError(f"LLM_PROVIDER non riconosciuto nel file .env: {provider}")