from google import genai

from src.llm.base_client import BaseLLMClient
from src.llm.prompt import PYTEST_SYSTEM_INSTRUCTION


class GeminiClient(BaseLLMClient):
	"""
	Client per Google Gemini via SDK ufficiale (google-genai).
	Implementa l'interfaccia BaseLLMClient.
	"""

	def __init__(self, model_name: str, base_url: str, api_key: str):
		"""
		Inizializza il client Gemini configurando i dettagli di connessione.

		Args:
			model_name (str): Identificativo del modello Gemini.
			base_url (str): Non usato con SDK, mantenuto per compatibilita.
			api_key (str): API key Google.
		"""
		if not api_key:
			raise ValueError("GEMINI_API_KEY non impostata nel file .env")

		self.model_name = model_name
		self.base_url = base_url.rstrip("/")
		self.api_key = api_key
		self.client = genai.Client(api_key=self.api_key)

	def generate_test(self, prompt: str) -> dict:
		"""
		Esegue una chiamata sincrona al modello Gemini per generare i test.

		Args:
			prompt (str): Il codice sorgente della funzione estratta dal dataset.

		Returns:
			dict: Il codice Pytest generato e il conteggio token.
		"""
		try:
			full_prompt = f"{PYTEST_SYSTEM_INSTRUCTION}\n\nCodice da testare:\n{prompt}"
			response = self.client.models.generate_content(
				model=self.model_name,
				contents=full_prompt,
				config=genai.types.GenerateContentConfig(
					temperature=0.1,
					max_output_tokens=800,
				),
			)

			text = (getattr(response, "text", "") or "").strip()
			usage = getattr(response, "usage_metadata", None)

			return {
				"code": text,
				"input_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
				"output_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
			}
		except Exception as e:
			print(f"[Errore Gemini] Generazione fallita: {e}")
			return {"code": "", "input_tokens": 0, "output_tokens": 0}
