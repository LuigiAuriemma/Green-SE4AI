import os
import time
from dotenv import load_dotenv

from src.llm.factory import LLMFactory
from src.dataset_manager import get_evalplus_dataset
from utils.metrics_logger import log_benchmark_result

def main():
    """
    Orchestratore principale del benchmark. Scorre cicliclemente il dataset
    ed esegue la pipeline di generazione e logging per ogni problema.
    """
    load_dotenv()

    # Configura qui il limite di problemi che vuoi testare (es. 2, 5, o None per tutti)
    LIMIT_PROBLEMI = 2

    dataset = get_evalplus_dataset(limit=LIMIT_PROBLEMI)
    if not dataset:
        print("[Errore] Dataset vuoto o non caricato.")
        return

    # Inizializzazione del client fuori dal ciclo per non ricrearlo ogni volta
    try:
        client = LLMFactory.get_client()
        provider = os.getenv("LLM_PROVIDER", "local").lower()
        if provider == "local":
            model_name = os.getenv("OLLAMA_MODEL", "novaforgeai/qwen2.5-3b:q4km")
        elif provider == "github":
            model_name = os.getenv("GITHUB_MODEL", "gpt-4o-mini")
        elif provider == "gemini":
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        else:
            raise ValueError(f"Provider non supportato: {provider}")
    except Exception as e:
        print(f"[Errore Factory] {e}")
        return

    print(f"\n=== INIZIO BENCHMARK SU {len(dataset)} PROBLEMI ===")


    # CICLO PRINCIPALE: Scorre i problemi uno alla volta
    for index, problema in enumerate(dataset):
        task_id = problema['task_id']
        prompt_codice = problema['full_code']

        print(f"\n[{index + 1}/{len(dataset)}] Elaborazione {task_id} con {model_name}...")
        
        start_time = time.time()
        status = "success"
        error_msg = ""
        codice_test_generato = ""
        prompt_tokens = 0
        completion_tokens = 0

        try:
            # Chiamata al modello (il timeout è gestito dentro slm_clients.py)
            result = client.generate_test(prompt_codice)
            codice_test_generato = result["code"]
            prompt_tokens = result["input_tokens"]
            completion_tokens = result["output_tokens"]
        except Exception as e:
            status = "failed"
            error_msg = str(e)
            print(f" -> [Errore] Generazione fallita per {task_id}: {e}")

        execution_time = time.time() - start_time
        print(f" -> [Timer] Completato in {execution_time:.2f} secondi.")

         # Scrittura dei dati (aggiorna o inserisce senza duplicare)
        log_benchmark_result(
                task_id=task_id,
                provider=provider,
                model_name=model_name,
                prompt_input=prompt_codice,
                output=codice_test_generato,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                execution_time=execution_time,
                status=status,
                error_msg=error_msg
            )

    if error_msg:
        print("\n=== BENCHMARK COMPLETATO === (fallimento)")
    else:
        print("\n=== BENCHMARK COMPLETATO ===")

if __name__ == "__main__":
    main()