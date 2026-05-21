import requests
from src.llm.base_client import BaseLLMClient
from src.llm.prompt import PYTEST_SYSTEM_INSTRUCTION

class SLMClient(BaseLLMClient):
    """
    Client per la gestione dell'inferenza locale tramite il servizio Ollama.
    Implementa l'interfaccia BaseLLMClient.
    """

    def __init__(self, model_name: str, base_url: str):
        """
        Inizializza il client locale configurando i dettagli di connessione all'API.

        Args:
            model_name (str): Identificativo del modello quantizzato caricato su Ollama.
            base_url (str): Endpoint HTTP di ascolto del demone locale di Ollama.
        """
        self.model_name = model_name
        self.provider = "local"  # Identificativo del provider per il logging e la Factory
        # Sanificazione dell'URL per evitare duplicazioni delle barre nei path successivi
        self.api_url = f"{base_url.rstrip('/')}/api/generate"

    def generate_test(self, prompt: str) -> dict:
        """
        Esegue una chiamata POST sincrona all'API di Ollama per generare i test.

        Args:
            prompt (str): Il codice sorgente della funzione estratta dal dataset.

        Returns:
            dict: Il codice Pytest generato pulito e il conteggio esatto dei token.
        """
        # Unione delle istruzioni di sistema centralizzate con il codice sorgente
        full_prompt = f"{PYTEST_SYSTEM_INSTRUCTION}\n\nCodice da testare:\n{prompt}"
        
        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,  # Disabilita lo streaming per ricevere il payload completo
            "options": {
                "temperature": 0.1
            }
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            
            # Estrazione sicura del testo e delle metriche fornite nativamente da Ollama
            return {
                "code": data.get("response", "").strip(),
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0)
            }
        except Exception as e:
            print(f"[Errore Ollama] Generazione fallita: {e}")
            raise e