import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')

def classify_model(model_name):
    """Semplice euristica per classificare i modelli in LLM e SLM."""
    name_lower = model_name.lower()
    if 'gpt' in name_lower or 'gemini' in name_lower or 'claude' in name_lower:
        return 'LLM'
    return 'SLM'

def load_data():
    eco_file = os.path.join("results", "eco_metrics.csv")
    eval_file = os.path.join("results", "evaluation", "evaluation_results.csv")
    
    if not os.path.exists(eco_file):
        raise FileNotFoundError(f"File non trovato: {eco_file}")
    if not os.path.exists(eval_file):
        raise FileNotFoundError(f"File non trovato: {eval_file}")
        
    df_eco = pd.read_csv(eco_file)
    df_eval = pd.read_csv(eval_file)
    
    return df_eco, df_eval

def prepare_data(df_eco, df_eval):
    df_eco['model_name'] = df_eco['model_name'].str.replace('/', '_').str.replace(':', '_')

    # Aggiungi classificazione tipo modello
    df_eco['model_type'] = df_eco['model_name'].apply(classify_model)
    df_eval['model_type'] = df_eval['model_name'].apply(classify_model)
    
    # ... [il resto della funzione] ...
    # Aggregazione evaluation
    # Calcola coverage media e test pass rate per modello e prompt_type
    df_eval['pass_rate'] = df_eval.apply(
        lambda row: row['passed'] / row['total_tests'] if row['total_tests'] > 0 else 0, 
        axis=1
    )
    
    eval_agg = df_eval.groupby(['model_name', 'prompt_type']).agg({
        'coverage': 'mean',
        'pass_rate': 'mean',
        'mutation_score': 'mean'
    }).reset_index()
    
    # Merge con eco metrics
    df_merged = pd.merge(df_eco, eval_agg, on=['model_name', 'prompt_type'], how='inner')
    
    # Creiamo un label combinato per rendere certi grafici più facili da leggere
    df_merged['config_label'] = df_merged['model_type'] + " (" + df_merged['prompt_type'] + ")"
    return df_merged, df_eval

def generate_plots(df_merged, df_eval, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")

    # -----------------------------------------------------
    # 1. Boxplot (o Barplot) Confronto Energia (RQ1, RQ2)
    # Mostriamo per ogni tipo di modello e prompt il consumo di energia.
    # -----------------------------------------------------
    plt.figure(figsize=(10, 6))

    ordine_x = ["LLM (green)", "LLM (raw)", "SLM (green)", "SLM (raw)"]
    
    if len(df_merged) > len(df_merged[['model_type', 'prompt_type']].drop_duplicates()):
        sns.boxplot(
            data=df_merged, 
            x='config_label', 
            y='energy_kwh', 
            palette= "Set2",
            order=ordine_x,
            hue='config_label',
            legend=False
        )
    else:
        sns.barplot(
            data=df_merged, 
            x='config_label', 
            y='energy_kwh', 
            palette= "Set2",
            order=ordine_x,
            hue='config_label',
            legend=False
        )
    plt.title('Energia Consumata (kWh) per Tipo Modello e Approccio (RAW vs GREEN)')
    plt.ylabel('Energia (kWh)')
    plt.xlabel('Tipo di Modello')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '1_energy_comparison.png'), dpi=300)
    plt.close()

    # -----------------------------------------------------
    # 2. Bar Chart Raggruppato Coverage LLM vs SLM
    # -----------------------------------------------------
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_merged, x='model_type', y='coverage', hue='prompt_type', palette="crest")
    plt.title('Coverage del Codice (%) - LLM vs SLM')
    plt.ylabel('Coverage Media (%)')
    plt.xlabel('Tipo di Modello')
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '2_coverage_comparison.png'), dpi=300)
    plt.close()

    # -----------------------------------------------------
    # 3. Scatter Plot: Coverage vs. Energy Consumption (RQ3-RQ6)
    # Permette di vedere il bilancio costo/qualità dei quadranti
    # -----------------------------------------------------
    plt.figure(figsize=(12, 7))
    sns.scatterplot(
        data=df_merged, 
        x='coverage', 
        y='energy_kwh', 
        hue='model_type', 
        style='prompt_type', 
        s=200, 
        palette="deep", 
        markers=['o', 'X']
    )
    
    # Etichette sui punti per capire esattamente chi è chi
    for i in range(df_merged.shape[0]):
        plt.text(
            df_merged['coverage'].iloc[i] + 0.5, 
            df_merged['energy_kwh'].iloc[i], 
            df_merged['model_name'].iloc[i], 
            horizontalalignment='left', 
            size='small', 
            color='black'
        )
        
    plt.title('Rapporto Qualità / Costo Energetico: Coverage vs Consumo (kWh)')
    plt.xlabel('Coverage Media (%) - (Qualità)')
    plt.ylabel('Energia (kWh) - (Costo)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '3_coverage_vs_energy_scatter.png'), dpi=300)
    plt.close()

    # -----------------------------------------------------
    # 4. Analisi Dettagliata per singola Task (Qualità)
    # Boxplot della coverage per valutare la varianza della qualità
    # -----------------------------------------------------
    plt.figure(figsize=(12, 6))
    df_eval['config_label'] = df_eval['model_type'] + "_" + df_eval['prompt_type']
    sns.boxplot(data=df_eval, x='config_label', y='coverage', palette="Set3")
    plt.title('Distribuzione della Coverage nei Singoli Task')
    plt.ylabel('Coverage (%)')
    plt.xlabel('Configurazione')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '4_task_coverage_boxplot.png'), dpi=300)
    plt.close()

    # -----------------------------------------------------
    # 5. Bar Chart Raggruppato Mutation Score LLM vs SLM
    # -----------------------------------------------------
    plt.figure(figsize=(10, 6))
    if 'mutation_score' in df_merged.columns:
        sns.barplot(data=df_merged, x='model_type', y='mutation_score', hue='prompt_type', palette="viridis")
        plt.title('Mutation Score (%) - LLM vs SLM')
        plt.ylabel('Mutation Score Medio (%)')
        plt.xlabel('Tipo di Modello')
        plt.ylim(0, 100)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '5_mutation_comparison.png'), dpi=300)
    plt.close()

    # -----------------------------------------------------
    # 6. Scatter Plot: Mutation Score vs. Energy Consumption
    # -----------------------------------------------------
    plt.figure(figsize=(12, 7))
    if 'mutation_score' in df_merged.columns:
        sns.scatterplot(
            data=df_merged, 
            x='mutation_score', 
            y='energy_kwh', 
            hue='model_type', 
            style='prompt_type', 
            s=200, 
            palette="deep", 
            markers=['o', 'X']
        )
        for i in range(df_merged.shape[0]):
            plt.text(
                df_merged['mutation_score'].iloc[i] + 0.5, 
                df_merged['energy_kwh'].iloc[i], 
                df_merged['model_name'].iloc[i], 
                horizontalalignment='left', 
                size='small', 
                color='black'
            )
        plt.title('Rapporto Qualità / Costo Energetico: Mutation Score vs Consumo (kWh)')
        plt.xlabel('Mutation Score Medio (%) - (Qualità)')
        plt.ylabel('Energia (kWh) - (Costo)')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '6_mutation_vs_energy_scatter.png'), dpi=300)
    plt.close()

    print(f"[Successo] Generati 6 grafici nella cartella: {output_dir}")

def main():
    print("Avvio Analisi dei Dati...")
    try:
        df_eco, df_eval = load_data()
        df_merged, df_eval_prepared = prepare_data(df_eco, df_eval)
        
        output_dir = os.path.join("results", "plots")
        generate_plots(df_merged, df_eval_prepared, output_dir)
        
        print("\n--- Riepilogo Analisi (Media per Categoria) ---")
        summary_cols = ['coverage', 'pass_rate', 'mutation_score', 'energy_kwh'] if 'mutation_score' in df_merged.columns else ['coverage', 'pass_rate', 'energy_kwh']
        summary = df_merged.groupby(['model_type', 'prompt_type'])[summary_cols].mean().reset_index()
        print(summary.to_string(index=False))
        
    except Exception as e:
        print(f"[Errore] Impossibile completare l'analisi: {e}")

if __name__ == "__main__":
    main()
