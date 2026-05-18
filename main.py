import os
import time
from dotenv import load_dotenv

from src.llm.factory import LLMFactory
from src.dataset_manager import get_evalplus_dataset
from src.utils.metrics_logger import log_benchmark_result

def esegui_singolo_benchmark(client, problema, provider: str, model_name: str) -> bool:
    """
    Esegue la pipeline di generazione e logging per un singolo problema del dataset.
    Ritorna True se la generazione è avvenuta senza eccezioni, False altrimenti.
    """
    task_id = problema['task_id']
    prompt_codice = problema['full_code']

    start_time = time.time()
    status = "success"
    error_msg = ""
    codice_test_generato = ""
    prompt_tokens = 0
    completion_tokens = 0

    try:
        # Chiamata al modello (il timeout è gestito dentro i client)
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

    # Scrittura dei dati (traccia sempre, ottima scelta energetica/green)
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

    return status == "success"


def main():
    """
    Orchestratore principale del benchmark. 
    Si occupa solo di configurare l'ambiente e guidare il ciclo.
    """
    load_dotenv()
    LIMIT_PROBLEMI = 2

    dataset = get_evalplus_dataset(limit=LIMIT_PROBLEMI)
    if not dataset:
        print("[Errore] Dataset vuoto o non caricato.")
        return

    try:
        # Ottimizzazione incapsulamento (dal nostro step precedente)
        client = LLMFactory.get_client()
        provider = getattr(client, "provider", "unknown_provider")
        model_name = getattr(client, "model_name", "unknown_model")
    except Exception as e:
        print(f"[Errore Factory] {e}")
        return

    print(f"\n=== INIZIO BENCHMARK SU {len(dataset)} PROBLEMI ===")
    print(f"Provider attivo: {provider} | Modello: {model_name}")

    # Contatore per tracciare i fallimenti totali lungo tutto il ciclo
    problemi_falliti = 0

    # CICLO PRINCIPALE: Adesso è snello e chiarissimo
    for index, problema in enumerate(dataset):
        print(f"\n[{index + 1}/{len(dataset)}] ", end="")
        
        # Deleghiamo il lavoro sporco alla funzione specializzata
        successo = esegui_singolo_benchmark(client, problema, provider, model_name)
        
        if not successo:
            problemi_falliti += 1

    # Report finale accurato (risolto il bug del controllo sull'ultimo elemento)
    if problemi_falliti > 0:
        print(f"\n=== BENCHMARK COMPLETATO === ({problemi_falliti}/{len(dataset)} problemi falliti)")
    else:
        print("\n=== BENCHMARK COMPLETATO CON SUCCESSO ===")


if __name__ == "__main__":
    main()