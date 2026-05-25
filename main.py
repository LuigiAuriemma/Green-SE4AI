import os
import time
from dotenv import load_dotenv
from ecologits import EcoLogits
from src.llm.factory import LLMFactory
from src.dataset_manager import get_evalplus_dataset
from src.eco_tracker import EcoTracker
from src.green_optimizer import optimize_code
from src.utils.metrics_logger import log_benchmark_result, log_eco_batch_result


def esegui_singolo_benchmark(client, problema, provider: str, model_name: str, prompt_type: str = "raw") -> tuple:
    """
    Esegue la pipeline di generazione e logging per un singolo problema del dataset.
    Ritorna una tupla: (bool_successo, cloud_kwh, cloud_co2_g)
    """
    task_id = problema['task_id']

    # SCELTA DELL'APPROCCIO
    if prompt_type == "green":
        prompt_codice = optimize_code(problema['full_code'])
    else:
        prompt_codice = problema['full_code']

    start_time = time.time()
    status = "success"
    error_msg = ""
    codice_test_generato = ""
    prompt_tokens = 0
    completion_tokens = 0
    cloud_kwh = 0.0
    cloud_co2_g = 0.0

    try:
        # Chiamata al modello
        result = client.generate_test(prompt_codice)
        codice_test_generato = result["code"]
        prompt_tokens = result["input_tokens"]
        completion_tokens = result["output_tokens"]
        cloud_kwh = result.get("cloud_energy_kwh", 0.0)
        cloud_co2_g = result.get("cloud_co2_g", 0.0)

    except Exception as e:
        status = "failed"
        error_msg = str(e)
        print(f" -> [Errore] Generazione fallita per {task_id}: {e}")

    execution_time = time.time() - start_time
    print(f" -> [Timer] Completato in {execution_time:.2f} secondi. Token In/Out: {prompt_tokens}/{completion_tokens}")

    # Scrittura dei dati
    log_benchmark_result(
        task_id=task_id,
        provider=provider,
        model_name=model_name,
        prompt_type=prompt_type,
        prompt_input=prompt_codice,
        output=codice_test_generato,
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        execution_time=execution_time,
        status=status,
        error_msg=error_msg
    )

    # Ritorna sia lo status che i consumi stimati
    return status == "success", cloud_kwh, cloud_co2_g


def main():
    """
    Orchestratore principale del benchmark.
    """
    load_dotenv()

    # Intercetta automaticamente le chiamate OpenAI e Google GenAI
    EcoLogits.init(providers=['openai'])
    LIMIT_PROBLEMI = 50

    # DECIDI QUALE PROMPT TESTARE ("raw" o "green")
    PROMPT_TYPE = "green"

    # Caricamento del dataset
    dataset = get_evalplus_dataset(limit=LIMIT_PROBLEMI)
    if not dataset:
        print("[Errore] Dataset vuoto o non caricato.")
        return

    # =======================================================
    # ESECUZIONE MIRATA DI UN SINGOLO RECORD
    # =======================================================
    # Imposta TARGET_TASK_ID con il task_id desiderato (es. 'HumanEval/2')
    # Lascia a None per eseguire l'intero dataset.
    TARGET_TASK_ID = None  # <-- Modifica qui se vuoi testare un singolo task

    if TARGET_TASK_ID:
        dataset = [p for p in dataset if p['task_id'] == TARGET_TASK_ID]
        if not dataset:
            print(f"[Attenzione] Nessun record trovato con task_id: {TARGET_TASK_ID}")
            return
        print(f"\n[Info] Esecuzione limitata al solo task: {TARGET_TASK_ID}")
    # =======================================================

    # Caricamento del modello di inferenza tramite Factory
    try:
        client = LLMFactory.get_client()
        provider = getattr(client, "provider", "unknown_provider")
        model_name = getattr(client, "model_name", "unknown_model")
    except Exception as e:
        print(f"[Errore Factory] {e}")
        return

    print(f"\n=== INIZIO BENCHMARK SU {len(dataset)} PROBLEMI ===")
    print(f"Provider: {provider} | Modello: {model_name} | Approccio: {PROMPT_TYPE.upper()}")

    problemi_falliti = 0

    # ==========================================
    # INIZIO TRACKER AMBIENTALE (EcoTracker)
    # ==========================================
    with EcoTracker() as sonda:
        for index, problema in enumerate(dataset):
            print(f"\n[{index + 1}/{len(dataset)}] Task: {problema['task_id']}", end="")

            successo, kwh_api, co2_api = esegui_singolo_benchmark(client, problema, provider, model_name,
                                                                  prompt_type=PROMPT_TYPE)

            #Aggiungiamo i consumi Cloud alla nostra sonda locale
            sonda.add_cloud_impacts(kwh_api, co2_api)

            if not successo:
                problemi_falliti += 1
    # ==========================================
    # FINE TRACKER AMBIENTALE
    # ==========================================



    # Report finale e Stampa delle Metriche Green Globali
    print("\n" + "=" * 50)
    if problemi_falliti > 0:
        print(f"=== BENCHMARK COMPLETATO === ({problemi_falliti}/{len(dataset)} problemi falliti)")
    else:
        print("=== BENCHMARK COMPLETATO CON SUCCESSO ===")

    print("\n--- REPORT ENERGETICO IBRIDO (LOCALE + CLOUD) ---")
    print(f"Tempo Esecuzione Totale: {sonda.latency_sec:.2f} secondi")
    print(f"Impatto RAM Locale (Delta): {sonda.ram_delta_mb:.2f} MB")
    print(f"Energia Totale Consumata:   {sonda.energy_kwh:.8f} kWh")
    print(f"Emissioni di CO2 Totali:    {sonda.co2_g:.6f} grammi")
    print("=" * 50)




    # ==========================================
    # SALVATAGGIO METRICHE AMBIENTALI
    # ==========================================
    log_eco_batch_result(
        provider=provider,
        model_name=model_name,
        prompt_type=PROMPT_TYPE,
        total_tasks=len(dataset),
        failed_tasks=problemi_falliti,
        latency_sec=sonda.latency_sec,
        ram_delta_mb=sonda.ram_delta_mb,
        energy_kwh=sonda.energy_kwh,
        co2_g=sonda.co2_g
    )


if __name__ == "__main__":
    main()