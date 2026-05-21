import os
import csv
import json
import sys
import subprocess
import xml.etree.ElementTree as ET

def sanitize_test_file(file_path: str):
    """
    Legge il file di test generato e lo purifica dagli artefatti tipici degli LLM
    (tag markdown, testo discorsivo non commentato, import fantasma) per garantire un'esecuzione equa.
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception as e:
        print(f"     [Errore Lettura per Sanificazione] {e}")
        return

    cleaned_lines = []
    # Parole chiave permesse a inizio riga
    approved_keywords = ('import', 'from', 'def', 'class', 'assert', '@', 'with', 'try', 'except', '#', 'print', 'if ', 'else:', 'return', 'elif ', 'for ', 'while ')
    placeholders = ['your_module', 'solution', 'submission', 'code', 'product']

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue

        # 1. Rimuove i blocchi di formattazione Markdown
        if stripped.startswith("```"):
            continue

        # 2. Rimuove gli import finti (es. from your_module import ...)
        if stripped.startswith("from ") and "import " in stripped:
            # Se è l'import ufficiale della nostra soluzione separata, lo salviamo!
            if "solution_humaneval" in stripped.lower():
                cleaned_lines.append(line)
                continue
                
            # Se invece contiene i placeholder generici dell'LLM (es: from solution import ...), lo commenta
            if any(p in stripped.lower() for p in placeholders):
                cleaned_lines.append(f"# {line}  # Commentato automaticamente per equità")
                continue

        # 3. Identifica il testo discorsivo non commentato a livello 0
        if len(line) == len(line.lstrip()):
            if any(stripped.startswith(kw) for kw in approved_keywords):
                cleaned_lines.append(line)
            elif any(c in stripped for c in ['=', '(', ')', '[', ']', '{', '}']) or stripped.startswith(('"', "'")):
                cleaned_lines.append(line)
            else:
                cleaned_lines.append(f"# {line}")
        else:
            if stripped.startswith("-") or stripped.startswith("*"):
                cleaned_lines.append(f"# {line}")
            else:
                cleaned_lines.append(line)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(cleaned_lines) + "\n")
    except Exception as e:
        print(f"     [Errore Scrittura Sanificazione] {e}")

def parse_pytest_xml(xml_path: str) -> dict:
    """Analizza il report XML temporaneo di pytest per estrarre le metriche avanzate."""
    if not os.path.exists(xml_path):
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0, "reason": "Nessun report generato o errore strutturale."}
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        testsuite = root.find("testsuite") if root.tag == "testsuites" else root
        if testsuite is None:
            testsuite = root
        
        total = int(testsuite.attrib.get("tests", 0))
        failures = int(testsuite.attrib.get("failures", 0))
        errors = int(testsuite.attrib.get("errors", 0))
        passed = total - failures - errors
        
        reason = ""
        if failures > 0 or errors > 0:
            for testcase in testsuite.findall("testcase"):
                fail_node = testcase.find("failure")
                if fail_node is None:
                    fail_node = testcase.find("error")
                if fail_node is not None:
                    reason = fail_node.attrib.get("message", "") or fail_node.text or "AssertionError"
                    reason = reason.strip().splitlines()[0]
                    break
                    
        return {"total": total, "passed": passed, "failed": failures, "errors": errors, "reason": reason if reason else "Nessun dettaglio"}
    except Exception as e:
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0, "reason": f"Errore parsing XML: {str(e)}"}


def update_benchmark_files(task_id: str, folder_model_id: str, new_status: str):
    """Aggiorna il campo 'test_verified_status' in benchmark_results.json e csv."""
    results_dir = "results"
    json_path = os.path.join(results_dir, "benchmark_results.json")
    csv_path = os.path.join(results_dir, "benchmark_results.csv")
    target_task = task_id.replace("_", "/") if "HumanEval_" in task_id else task_id

    # 1. Aggiornamento JSON
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            updated = False
            for record in data:
                rec_model_clean = record.get("model_name", "").lower().replace("/", "_").replace(":", "_").replace(" ", "_")
                rec_prompt_type = record.get("prompt_type", "raw").lower()
                expected_folder_id = f"{rec_model_clean}-{rec_prompt_type}"
                
                if record.get("task_id") == target_task and folder_model_id.lower() == expected_folder_id:
                    record["test_verified_status"] = new_status
                    updated = True
            if updated:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e: 
            print(f"     [Errore Aggiornamento JSON] {e}")

    # 2. Aggiornamento CSV
    if os.path.exists(csv_path):
        try:
            rows, fieldnames = [], []
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames if reader.fieldnames else []
                if "test_verified_status" not in fieldnames: 
                    fieldnames.append("test_verified_status")
                for row in reader:
                    rec_model_clean = row.get("model_name", "").lower().replace("/", "_").replace(":", "_").replace(" ", "_")
                    rec_prompt_type = row.get("prompt_type", "raw").lower()
                    expected_folder_id = f"{rec_model_clean}-{rec_prompt_type}"
                    
                    if row.get("task_id") == target_task and folder_model_id.lower() == expected_folder_id:
                        row["test_verified_status"] = new_status
                    elif "test_verified_status" not in row:
                        row["test_verified_status"] = "pending"
                    rows.append(row)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e: 
            print(f"     [Errore Aggiornamento CSV] {e}")


def main():
    base_dir = os.path.join("results", "AI_test")
    eval_dir = os.path.join("results", "evaluation")
    os.makedirs(eval_dir, exist_ok=True)
    
    if not os.path.exists(base_dir):
        print(f"[Errore] Cartella '{base_dir}' non trouvata. Lancia prima main.py.")
        return

    print("\n==================================================================")
    print("         AVVIO VALUTAZIONE AVANZATA SUITE (SANITY & EXECUTION)    ")
    print("==================================================================")

    # 🔍 VERIFICA DI SICUREZZA: Pytest è effettivamente installato nel .venv corrente?
    try:
        check_cmd = [sys.executable, "-m", "pytest", "--version"]
        res_check = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res_check.returncode != 0:
            print("[ERRORE CRITICO] Pytest non è installato o non è accessibile nel tuo ambiente virtuale (.venv).")
            print(f"Percorso interprete corrente: {sys.executable}")
            print("Per favore, installa pytest eseguendo sul tuo terminale:")
            print("   pip install pytest")
            print("==================================================================\n")
            return
    except Exception as e:
        print(f"[ERRORE CRITICO] Impossibile eseguire il controllo di pytest: {e}")
        return

    modelli = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not modelli:
        print("[Avviso] Nessuna cartella di modelli trovata.")
        return

    evaluation_report = []

    for model_id in modelli:
        model_path = os.path.join(base_dir, model_id)
        
        # Separazione logica di model_name e prompt_type dal nome della cartella
        actual_model_name = model_id
        actual_prompt_type = "raw"
        if model_id.endswith("-green"):
            actual_model_name = model_id[:-6]
            actual_prompt_type = "green"
        elif model_id.endswith("-raw"):
            actual_model_name = model_id[:-4]
            actual_prompt_type = "raw"
            
        print(f"\n[Modello] Testing suite per: {actual_model_name} (Prompt: {actual_prompt_type.upper()})")
        print("-" * 66)
        
        # Raccogliamo solo i file di test generati (escludendo i file solution_*.py dedicati alla coverage)
        test_files = sorted(
            [f for f in os.listdir(model_path) if f.startswith("test_HumanEval_") and f.endswith(".py")],
            key=lambda x: int(x.split("_")[2].split(".")[0])
        )
        
        for file_name in test_files:
            file_path = os.path.join(model_path, file_name)
            task_id_extracted = file_name.replace("test_", "").replace(".py", "")
            
            print(f"  -> {file_name}: ", end="", flush=True)
            
            # Controllo file vuoto
            if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
                print("[SALTATO] (File vuoto)")
                update_benchmark_files(task_id_extracted, model_id, "pending")
                evaluation_report.append({
                    "model_name": actual_model_name, "prompt_type": actual_prompt_type, "task_id": task_id_extracted.replace("_", "/"), "execution_status": "SKIPPED_EMPTY",
                    "coverage": 0.0,
                    "coverage_report": "N/A",
                    "total_tests": 0, "passed": 0, "failed": 0, "errors": 0, "failure_reason": "Generazione fallita o file vuoto"
                })
                continue

            # ✨ PASSO DI EQUITÀ: Sanifichiamo il file prima di darlo a Pytest
            sanitize_test_file(file_path)

            xml_temp_path = os.path.join(eval_dir, f"temp_{model_id}_{task_id_extracted}.xml")
            cov_temp_path = os.path.join(eval_dir, f"temp_{model_id}_{task_id_extracted}_cov.json")
            html_cov_dir = os.path.join(eval_dir, "coverage_html", model_id, task_id_extracted)
            html_index_path = os.path.join(html_cov_dir, "index.html")
            
            # 1. IDENTIFICHIAMO IL MODULO DELLA SOLUZIONE (es. "solution_HumanEval_0")
            solution_module = f"solution_{task_id_extracted}"
            solution_file_name = f"{solution_module}.py"

            # 2. MODIFICHIAMO IL COMANDO: Eseguiamo il file di test, ma misuriamo la coverage SOLO sul modulo soluzione
            cmd = [
                sys.executable, "-m", "pytest", 
                file_path, 
                f"--junitxml={xml_temp_path}", 
                f"--cov={solution_module}", # <--- Cambiato qui! Bersaglio impostato sulla funzione, non sul test.
                f"--cov-report=json:{cov_temp_path}", 
                f"--cov-report=html:{html_cov_dir}", 
                "-q"
            ]
            
            try:
                # 3. CONFIGURIAMO IL PYTHONPATH affinché l'interprete isolato trovi la soluzione nella cartella del modello
                current_env = os.environ.copy()
                current_env["PYTHONPATH"] = model_path + os.pathsep + current_env.get("PYTHONPATH", "")

                # Passiamo 'env=current_env' al sottoprocesso
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10, env=current_env)
                
                # Se l'XML non esiste, quasi certamente pytest ha fallito la collection a monte per syntax/import error
                if not os.path.exists(xml_temp_path):
                    status_string = "EXECUTION_ERROR"
                    error_detail = res.stderr.strip() or res.stdout.strip()
                    
                    if "ModuleNotFoundError" in error_detail:
                        status_string = "IMPORT_ERROR"
                    elif "SyntaxError" in error_detail:
                        status_string = "SYNTAX_ERROR"
                    
                    reason_detail = error_detail.splitlines()[-1] if error_detail else "Pytest è crashato in fase di import/collection."
                    print(f"[{status_string}] -> Errore durante l'avvio o l'importazione.")
                    print(f"     Dettaglio: {reason_detail}")
                    
                    update_benchmark_files(task_id_extracted, model_id, "tested")
                    evaluation_report.append({
                        "model_name": actual_model_name,
                        "prompt_type": actual_prompt_type,
                        "task_id": task_id_extracted.replace("_", "/"), 
                        "execution_status": status_string,
                        "coverage": 0.0,
                        "coverage_report": "N/A",
                        "total_tests": 0, "passed": 0, "failed": 0, "errors": 0, 
                        "failure_reason": error_detail[:300]
                    })
                    continue

                metrics = parse_pytest_xml(xml_temp_path)
                
                # 4. PARSING DELLA COVERAGE DELLA SOLUZIONE
                coverage = 0.0
                if os.path.exists(cov_temp_path):
                    try:
                        with open(cov_temp_path, "r", encoding="utf-8") as f:
                            cov_data = json.load(f)
                            # Cerchiamo i dati relativi al file della soluzione nel report JSON
                            for k, v in cov_data.get("files", {}).items():
                                if solution_file_name in k: # <--- Cambiato qui! Cerca la soluzione e non il test.
                                    coverage = v.get("summary", {}).get("percent_covered", 0.0)
                                    break
                    except Exception:
                        pass

                # Determinazione avanzata dello stato basata sui risultati estratti
                if metrics["failed"] == 0 and metrics["errors"] == 0 and metrics["total"] > 0:
                    status_string = "PASSED"
                elif metrics["total"] == 0:
                    status_string = "NO_TESTS_COLLECTED"
                else:
                    status_string = "FAILED"

                print(f"[{status_string}] -> {metrics['passed']}/{metrics['total']} Passati", end="")
                if status_string not in ["PASSED", "NO_TESTS_COLLECTED"]:
                    print(f" | Errore: {metrics['reason']}")
                elif status_string == "NO_TESTS_COLLECTED":
                    print(f" | Dettaglio: Nessuna funzione di test valida raccolta")
                else:
                    print("")
                
                update_benchmark_files(task_id_extracted, model_id, "tested")
                
                evaluation_report.append({
                    "model_name": actual_model_name, "prompt_type": actual_prompt_type, "task_id": task_id_extracted.replace("_", "/"), "execution_status": status_string,
                    "coverage": round(coverage, 2),
                    "coverage_report": str(os.path.abspath(html_index_path)) if os.path.exists(html_index_path) else "N/A",
                    "total_tests": metrics["total"], "passed": metrics["passed"], "failed": metrics["failed"], "errors": metrics["errors"], "failure_reason": metrics["reason"]
                })

            except subprocess.TimeoutExpired:
                print("[TIMEOUT] (Possibile loop)")
                update_benchmark_files(task_id_extracted, model_id, "tested")
                evaluation_report.append({
                    "model_name": actual_model_name, "prompt_type": actual_prompt_type, "task_id": task_id_extracted.replace("_", "/"), "execution_status": "TIMEOUT",
                    "coverage": 0.0,
                    "coverage_report": "N/A",
                    "total_tests": 0, "passed": 0, "failed": 0, "errors": 0, "failure_reason": "Timeout esecuzione"
                })
            finally:
                if os.path.exists(xml_temp_path): 
                    os.remove(xml_temp_path)
                if os.path.exists(cov_temp_path): 
                    os.remove(cov_temp_path)

    # Scrittura Report Dedicati
    with open(os.path.join(eval_dir, "evaluation_results.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation_report, f, indent=4, ensure_ascii=False)
    if evaluation_report:
        with open(os.path.join(eval_dir, "evaluation_results.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=evaluation_report[0].keys())
            writer.writeheader()
            writer.writerows(evaluation_report)

    print("\n==================================================================")
    print(f" VALUTAZIONE COMPLETATA! I report avanzati sono in '{eval_dir}/'")
    print("==================================================================\n")

if __name__ == "__main__":
    main()