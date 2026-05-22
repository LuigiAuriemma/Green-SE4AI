# Green-SE4AI

Green-SE4AI è un framework per valutare e ottimizzare l'impatto ambientale (Green AI) nella generazione automatica di unit test tramite modelli di Intelligenza Artificiale (LLM/SLM). Il progetto misura non solo le metriche di successo del codice generato, ma anche i consumi energetici del sistema ospitante e in cloud, stimando le emissioni di CO2 per tutta la fase di inferenza e test.

Il progetto introduce, inoltre, un approccio "Green" applicando tecniche di ottimizzazione al codice sorgente prima che venga fornito come prompt al modello, con lo scopo di ridurre il dispendio di token elaborati (e, di conseguenza, risparmiare i costi energetici e monetari) valutando che esso non vada ad impattare la qualità finale dei risultati.

## Struttura del Progetto

- **`main.py`**: L'orchestratore principale utilizzato per eseguire i benchmark.
- **`src/dataset_manager.py`**: Modulo che interagisce con le API di Hugging Face per reperire il benchmark dataset di riferimento (viene utilizzato `evalplus/humanevalplus`).
- **`src/green_optimizer.py`**: Contiene il nodo d'ottimizzazione (`GreenTransformer`). Questo script esplora ed altera l'albero sintattico astratto (AST) frammento di codice inviatogli e ne riduce il payload depennando metadati che intasano token (type hints, docstring, asserzioni/logger interni) e attuando tecniche di offuscamento ai nomi delle variabili.
- **`src/eco_tracker.py`**: Un context manager personalizzato in cui convogliano la logica di `CodeCarbon` e della libreria `psutil` mirato a tracciare utilizzo della RAM, impatto CPU e quantificazione dei kilovattora e dei grammi di CO2, estesa a coprire i calcoli di tracking effettuati da `EcoLogits` che computano i ratei per l'uso delle API Cloud ospitanti l'infrastruttura d'inferenza genAI in uso.
- **`src/llm/`**: Gestisce il layer d'interfacciamento fra questo modulo e i provider con cui instanziare il modello tramite architettura a Factory Pattern.
- **`advanced_evaluate_test.py`**: Modulo dedicato alla sanificazione (pulizia) dei test generati dagli LLM (rimozione di markdown, finti import) e al parsing dei risultati avanzati dai report XML di pytest.
- **`data_analysis.py`**: Script per il caricamento dei data results, l'aggregazione delle metriche statistiche in categorie (LLM vs SLM, approccio "raw" vs "green") e la generazione di plot grafici ambientali e per coverage. 
- **`results/`**: Contiene la stesura materiale della reference elaborata dal modello con i test generati allegati per permettere un'eventuale esplorazione della Code Coverage a posteriori, unito ai classici log CSV/JSON che fungono da rendiconto energetico / temporale del benchmark appena eseguito.

## Installazione

1. Clona il repository
2. Per comodità ed evitare collisioni di pacchetti globali, è conigliato l'utilizzo di un ambiente virtuale.
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
4. Configura le variabili d'ambiente creando un file `.env` a livello di radice aggiungendo i token di Hugging Face per l'accesso ai dataset e le chiavi API d'accesso a chi elaborerà i prompt artificiali:
   ```env
    LLM_PROVIDER=github o local o gemini
    OLLAMA_BASE_URL=il_base_url
    OLLAMA_MODEL=il_modello_ollama

    HUGGINGFACE_TOKEN=il_tuo_token

    GITHUB_TOKEN=il_tuo_token
    GITHUB_BASE_URL=il_base_url
    GITHUB_MODEL=il_modello_da_utilizzare
   ```

## Regole d'Uso e Avvio

Per eseguire uno slot di benchmarking ai fini di rilevamenti test e monitoraggio green, posizionati sulla radice ed esegui:
```bash
python main.py
```

Smanettando all'interno di `main.py` è possibile configurare esecuzioni ridotte o su misura:
- **`LIMIT_PROBLEMI`**: Setta per quali e per quanti problemi limitare lo scaricamento dal dataset HF per agevolare iterazioni di testing pre-produzione.
- **`PROMPT_TYPE`**: Da configurare a proprio piacimento su `"raw"` o `"green"`, determina il passaggio per il processamento Green del prompt (tramite `green_optimizer.py`) prima dell'iniezione all'LLM.

Una volta completata l'esecuzione del benchmark principale (ovvero al termine dell'elaborazione di `main.py`), puoi proseguire con la pipeline di valutazione e plotting:

1. **Esecuzione dei test e Valutazione (Coverage automatica)**:
   ```bash
   python advanced_evaluate_test.py
   ```
   Questo script setaccerà la cartella `results/AI_test/`, eliminerà le "allucinazioni" discorsive dei modelli e avvierà `pytest` sulle soluzioni isolate. La directory `results/evaluation/` si riempirà automaticamente con l'HTML per la metrica di Code Coverage globale.

2. **Generazione e Plot dei Grafici (Data Analysis)**:
   ```bash
   python data_analysis.py
   ```
   Sfrutterà le librerie statistiche prelevando i dump log ambientali e valutativi, per sfornare immagini PNG riepilogative direttamente nella cartella `results/plots/` mettendo a stretto confronto consumo e affidabilità.

## Il Flusso Operativo del Framework

1. **Estrazione Dataset**: Carica una porzione configurabile del dataset _HumanEval+_ ad alto tasso di testing d'uso pratico e algoritmi implementativi base.
2. **Ottimizzazione (Opzionale)**: Se specificato (`PROMPT_TYPE="green"`), l'involucro elabora la pre-generazione ed elide i nodi sintattici non indispensabili offuscando il testo.
3. **Generazione e Testing**: Tramite la classe `LLMFactory` (che preleva il giusto provider configurato) richiede formalmente l'invocazione di esecuzione alla classe GenAI di stendere test unitari da un file/contesto input.
4. **Profilazione Ambientale**: Nel retroscena interviene costantemente CodeCarbon / EcoLogits andando ad emettere dei log post-chiamata API unificati di durata computazionale, delta MB della RAM assorbito e l'effettivo inquinamento di scala unificatrice in grammi e chilo-watt in locale e distribuito alle API in Cloud.
5. **Report & Output**: Redige cartelle ed esiti di resoconti (file HTML coverage o raw testing format) ordinati opportunamente su `results/`. In un passaggio secondario potranno prestarsi a studi con `data_analysis.py`.

## Valutazione e Analisi dei Dati (Post-Processing)

Una volta terminata l'elaborazione del `main.py`, il framework espone tool aggiuntivi per ripulire l'output ed esplorare graficamente le metriche raccolte:

1. **Sanificazione e Testing Avanzato (`advanced_evaluate_test.py`)**: Provvede a igienizzare il codice generato rimuovendo preventivamente gli artefatti tipici ed involontari delle GenAI (come blocchi markdown, import fantasma "solution", chiacchiere e testo discorsivo). Attua un parsing profondo XML dei test eseguiti con Pytest da cui si ricava numero di passaggi, e motivi di crash.
2. **Data Analysis & Plotting (`data_analysis.py`)**: Carica i file CSV storici dentro `results/` e performa un "merge" tra le pure performance qualitative del codice generato (pass rate, code coverage, mutation score) e la reale efficienza energetica raggiunta. Produce in automatico comparazioni grafiche sfruttando _seaborn/matplotlib_ (salvate per impostazione predefinita in directory come `results/plots/`).

### Metriche Analizzate e Valutazione dei Test

Il framework stila un resoconto che bilancia due sfere fondamentali: il costo ambientale e la qualità del codice generato. Per valutare l'effettiva bontà dei test prodotti dall'AI (ovvero assicurarsi che non siano solo sintatticamente corretti ma anche validi intercettatori di bug), analizziamo:

**1. Metriche Qualitative (Bontà dei Test):**
- **Pass Rate**: Tramite il parsing XML di pytest valutiamo la percentuale di test che passano con successo sul totale dei test eseguibili. Questo ci consente di scartare output contenenti asserzioni "allucinate".
- **Code Coverage**: Sfruttando `pytest-cov`, tracciamo la percentuale esatta di linee (line coverage) e logiche condizionali (branch coverage) della funzione originale che i test della GenAI riescono ad attraversare. Un'elevata code coverage denota una buona comprensione del framework logico esplorativo da parte del modello.
- **Mutation Score**: Valutiamo l'affidabilità empirica dei test. Modificando visivamente ed artificialmente il codice sorgente (introducendo bug mirati o alterando operatori logici), misuriamo quanti di questi bug vengono effettivamente fatti fallire dal test. È il miglior discriminante per differenziare dei test ben costruiti da test superficiali che fanno passare anche codice rotto.

**2. Metriche Ambientali e Performance (Green AI):**
- **Energia Consumata Ibrida (kWh)**: Calcolata unendo in tempo reale lo sforzo locale (spesa energetica CPU e consumo RAM analizzato con `CodeCarbon` e `psutil`) al costo energetico architetturale remoto del LLM in base ai token consumati (tramite `EcoLogits`).
- **Emissioni CO2 (g)**: Stima delle emissioni di anidride carbonica in base all'Energy Mix del server cloud e del PC utente host.
- **Latenza Computazionale (s)**: Il tempo impiegato per completare in maniera utile l'intero task di inferenza asincrona ai server e successiva costruzione del file test in locale.

Tra i principali output visivi e grafici generati dallo script di analisi, troviamo:
- **Confronto Energetico (Energy Comparison)**: Boxplot (o Barplot) statistici che evidenziano i consumi (in kWh) isolando le diverse famiglie di GenAI (`LLM` vs `SLM`) e validando al tempo stesso quanto l'approccio `green` influisca sul dispendio.
- **Analisi Qualitativa (Coverage & Pass Rate)**: Istogrammi raggruppati che esaminano la percentuale di suite andate a buon fine e la pura code coverage raggiunta. Torna essenziale per assicurarsi che i prompt compressi ambientalmente non degradino le capacità diagnostiche generate.
- **Relazione Emissioni CO2 / Performance (Opzionale)**: Mappature che affiancano le stime in grammi emessi all'accuratezza software ottenuta tramite le sonde ibridate da *psutil*, *CodeCarbon* e *EcoLogits*.
