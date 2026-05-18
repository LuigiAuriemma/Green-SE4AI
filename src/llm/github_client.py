from openai import OpenAI

from src.llm.base_client import BaseLLMClient
from src.llm.prompt import PYTEST_SYSTEM_INSTRUCTION


class LLMClient(BaseLLMClient):
	"""
	Client per GitHub Models tramite OpenAI SDK.
	Implementa l'interfaccia BaseLLMClient.
	"""

	def __init__(self, model_name: str, base_url: str, api_key: str):
		"""
		Inizializza il client cloud configurando i dettagli di connessione.

		Args:
			model_name (str): Identificativo del modello nel catalogo GitHub Models.
			base_url (str): Endpoint base per GitHub Models.
			api_key (str): Token GitHub con permesso Models: Read-only.
		"""
		if not api_key:
			raise ValueError("GITHUB_TOKEN non impostato nel file .env")

		self.model_name = model_name
		self.client = OpenAI(base_url=base_url, api_key=api_key)

	def generate_test(self, prompt: str) -> dict:
		"""
		Esegue una chiamata sincrona al modello cloud per generare i test.

		Args:
			prompt (str): Il codice sorgente della funzione estratta dal dataset.

		Returns:
			dict: Il codice Pytest generato e il conteggio token.
		"""
		try:
			response = self.client.chat.completions.create(
				model=self.model_name,
				messages=[
					{"role": "system", "content": PYTEST_SYSTEM_INSTRUCTION},
					{"role": "user", "content": f"Codice da testare:\n{prompt}"},
				],
				temperature=0.1,
				max_tokens=800,
			)

			message = response.choices[0].message.content or ""
			usage = response.usage

			return {
				"code": message.strip(),
				"input_tokens": getattr(usage, "prompt_tokens", 0),
				"output_tokens": getattr(usage, "completion_tokens", 0),
			}
		except Exception as e:
			print(f"[Errore GitHub Models] Generazione fallita: {e}")
			raise e
