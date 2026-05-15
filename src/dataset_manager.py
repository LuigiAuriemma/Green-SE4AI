import os
from dotenv import load_dotenv
from datasets import load_dataset

# Carica le variabili nascoste dal file .env nel sistema
load_dotenv()

def get_evalplus_dataset(limit=None):
    """
    Carica il dataset EvalPlus (HumanEval+) da Hugging Face e lo prepara per il task di generazione test.

    :param limit: Numero intero opzionale per limitare i risultati (es. 10 per fare test veloci).
    :return: Lista di dizionari contenenti id, firma, codice e docstring.
    """

    print("Scaricamento del dataset EvalPlus in corso...")

    hf_token = os.environ.get("HUGGINGFACE_TOKEN")
    # Carica il dataset.
    dataset = load_dataset("evalplus/humanevalplus", token=hf_token)
    # HumanEval ha un solo split di dati chiamato "test"
    raw_data = dataset["test"]
    processed_data = []

    # Iteriamo sui dati grezzi di humaneval ottenuti da huggingface
    for i, item in enumerate(raw_data):
        # Se abbiamo impostato un limite e lo abbiamo raggiunto, interrompiamo il ciclo
        if limit is not None and i >= limit:
            break

        # Creiamo un dizionario pulito solo con le informazioni necessarie
        processed_item = {
            "task_id": item["task_id"],
            "entry_point": item["entry_point"],  # Il nome della funzione
            "prompt": item["prompt"],  # Contiene import, firma e docstring
            "canonical_solution": item["canonical_solution"],  # Il corpo della funzione funzionante

            # Questa è la stringa finale che passeremo all'IA o all'Optimizer
            "full_code": item["prompt"] + item["canonical_solution"]
        }
        processed_data.append(processed_item)

    print(f"Dataset caricato: {len(processed_data)} problemi estratti e preparati.")
    return processed_data
