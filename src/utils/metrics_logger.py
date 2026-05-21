import csv
import json
import os
from datetime import datetime

def log_benchmark_result(task_id, provider, model_name, prompt_input, output, input_tokens, output_tokens, execution_time, status="success", error_msg=""):
    """
    Salva i dati di benchmark separando la soluzione (codice da testare) dai test dell'LLM,
    permettendo un calcolo reale della code coverage della funzione.
    """
    if status == "success" and (not output or not output.strip()):
        return
    safe_task_id = task_id.replace("/", "_")
    
    base_dir = "results"
    prompts_dir = os.path.join(base_dir, "prompts")
    tests_dir = os.path.join(base_dir, "AI_test")
    json_file = os.path.join(base_dir, "benchmark_results.json")
    csv_file = os.path.join(base_dir, "benchmark_results.csv")
    
    os.makedirs(prompts_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)

    safe_model_name = (
        model_name.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )
    model_tests_dir = os.path.join(tests_dir, safe_model_name)
    os.makedirs(model_tests_dir, exist_ok=True)

    # 1. Scrittura del file di prompt (conservato per storico nel vecchio percorso)
    prompt_path = os.path.join(prompts_dir, f"{safe_task_id}.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt_input)

    # 2. CREAZIONE DEL FILE SOLUZIONE (Il codice che deve subire il test di coverage)
    solution_filename = f"solution_{safe_task_id}"
    solution_path = os.path.join(model_tests_dir, f"{solution_filename}.py")
    with open(solution_path, "w", encoding="utf-8") as f:
        f.write(prompt_input)

    # 3. CREAZIONE DEL FILE DI TEST (Contiene solo i test dell'LLM + import dinamico)
    test_path = os.path.join(model_tests_dir, f"test_{safe_task_id}.py")
    with open(test_path, "w", encoding="utf-8") as f:
        if status == "failed":
            contenuto_test = ""
        else:
            # Iniettiamo l'importazione automatica per collegare il test alla soluzione separata
            contenuto_test = (
                f"from {solution_filename} import *\n\n"
                f"# ==========================================\n"
                f"# TEST GENERATI AUTOMATICAMENTE DALL'LLM\n"
                f"# ==========================================\n\n"
                f"{output}"
            )
        f.write(contenuto_test)

    # Caricamento del registro JSON esistente
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
        except json.JSONDecodeError:
            records = []
    else:
        records = []

    # Struttura del nuovo record corrente (aggiunto anche il percorso della soluzione)
    new_record = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "model_name": model_name,
        "execution_time_seconds": round(execution_time, 2),
        "status": status,
        "error_message": error_msg,
        "metrics": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        },
        "prompt_file_path": prompt_path,
        "solution_file_path": solution_path,  # <--- Tracciato nel JSON
        "test_file_path": test_path,
        "test_verified_status": "pending"
    }

    def is_same_config(record):
        return (
            record.get("task_id") == task_id
            and record.get("provider") == provider
            and record.get("model_name") == model_name
        )

    filtered_records = [record for record in records if not is_same_config(record)]
    if len(filtered_records) != len(records):
        print(f"[Logger] Record esistente aggiornato per {task_id} ({model_name}).")
    else:
        print(f"[Logger] Nuovo record registrato per {task_id} ({model_name}).")

    filtered_records.append(new_record)
    records = filtered_records

    # Salvataggio su disco (JSON)
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4, ensure_ascii=False)

    # Salvataggio CSV
    fieldnames = [
        "task_id", "timestamp", "provider", "model_name", "execution_time_seconds",
        "status", "error_message", "input_tokens", "output_tokens", "total_tokens",
        "prompt_file_path", "solution_file_path", "test_file_path", "test_verified_status"
    ]

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            metrics = record.get("metrics", {})
            writer.writerow({
                "task_id": record.get("task_id", ""),
                "timestamp": record.get("timestamp", ""),
                "provider": record.get("provider", ""),
                "model_name": record.get("model_name", ""),
                "execution_time_seconds": record.get("execution_time_seconds", ""),
                "status": record.get("status", ""),
                "error_message": record.get("error_message", ""),
                "input_tokens": metrics.get("input_tokens", ""),
                "output_tokens": metrics.get("output_tokens", ""),
                "total_tokens": metrics.get("total_tokens", ""),
                "prompt_file_path": record.get("prompt_file_path", ""),
                "solution_file_path": record.get("solution_file_path", ""), # <--- Tracciato nel CSV
                "test_file_path": record.get("test_file_path", ""),
                "test_verified_status": record.get("test_verified_status", ""),
            })


def log_eco_batch_result(provider, model_name, prompt_type, total_tasks, failed_tasks, latency_sec, ram_delta_mb,
                         energy_kwh, co2_g):
    """
    Salva le metriche ambientali e di sistema dell'intero batch in un file CSV dedicato.
    """
    base_dir = "results"
    os.makedirs(base_dir, exist_ok=True)
    csv_file = os.path.join(base_dir, "eco_metrics.csv")

    # Controlliamo se il file esiste già per capire se dobbiamo scrivere l'intestazione
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, "a", encoding="utf-8", newline="") as f:
        fieldnames = [
            "timestamp", "provider", "model_name", "prompt_type", "total_tasks", "failed_tasks",
            "total_latency_sec", "ram_delta_mb", "energy_kwh", "co2_g"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        # Funzione per estrarre il numero puro (poichè EcoLogits restituisce un intervallo)
        def extract_number(val):
            try:
                # Se è già un numero o un float puro, lo converte subito
                return float(val)
            except (ValueError, TypeError):
                # Se fallisce, lo trasforma in stringa e cerca il valore medio
                s = str(val)
                if 'mean=' in s:
                    # Taglia a "mean=" e prende il primo numero che trova dopo
                    numero_sporco = s.split('mean=')[1].split()[0]
                    return float(numero_sporco)
                elif 'min=' in s:
                    # se non c'è mean, prende il min
                    numero_sporco = s.split('min=')[1].split()[0]
                    return float(numero_sporco)

                # se è il formato con parentesi quadre
                return float(s.split()[0])

        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model_name": model_name,
            "prompt_type": prompt_type,
            "total_tasks": total_tasks,
            "failed_tasks": failed_tasks,
            "total_latency_sec": round(extract_number(latency_sec), 4),
            "ram_delta_mb": round(extract_number(ram_delta_mb), 4),
            "energy_kwh": round(extract_number(energy_kwh), 8),
            "co2_g": round(extract_number(co2_g), 6)
        })
    print(f"[Logger] Metriche ambientali salvate in {csv_file}")