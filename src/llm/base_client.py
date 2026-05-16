from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    """
    Classe astratta di interfaccia (Interface Pattern) per i client LLM/SLM.
    Garantisce il polimorfismo tra le implementazioni locali (Ollama) e cloud (OpenAI).
    """
    
    @abstractmethod
    def generate_test(self, prompt: str) -> dict:
        """
        Invia il codice sorgente al modello per generare la suite di test Pytest.

        Args:
            prompt (str): Il codice completo della funzione da testare (firma + corpo).

        Returns:
            dict: Dizionario contenente il codice generato e i metadati di consumo token.
                  Formato: {"code": str, "input_tokens": int, "output_tokens": int}
        """
        pass