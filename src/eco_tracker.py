import time
import psutil
import os
from codecarbon import EmissionsTracker


class EcoTracker:
    """
    Context Manager che avvolge un blocco di codice per misurarne:
    - Tempo di esecuzione (Latenza in secondi)
    - Consumo di memoria RAM (Delta in MB)
    - Energia consumata (kWh)
    - Emissioni stimate (Grammi di CO2)
    """

    def __init__(self):
        # Inizializziamo CodeCarbon.
        # log_level="error" evita che spami la console ad ogni misurazione
        # save_to_file=False evita la creazione automatica di file CSV sparsi (li gestiremo noi)
        self.tracker = EmissionsTracker(
            log_level="error",
            save_to_file=False,
            measure_power_secs=1  # Campionamento più frequente (1 sec) per inferenze veloci
        )
        self.process = psutil.Process(os.getpid())

        # Variabili che conterranno i risultati finali
        self.latency_sec = 0.0
        self.ram_delta_mb = 0.0
        self.energy_kwh = 0.0
        self.co2_g = 0.0

    def __enter__(self):
        """Fotografia iniziale delle risorse (eseguita all'inizio del blocco 'with')"""
        self.start_time = time.perf_counter()
        self.start_ram = self.process.memory_info().rss

        # Avvia il tracciamento energetico
        self.tracker.start()

        return self  # Restituisce l'istanza per poter leggere le metriche dopo

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fotografia finale e calcolo dei delta (eseguita alla fine del blocco 'with')"""
        # Ferma il tracciamento (restituisce i kg di CO2)
        co2_kg = self.tracker.stop()

        self.end_time = time.perf_counter()
        self.end_ram = self.process.memory_info().rss

        # Calcolo Metriche Finali
        self.latency_sec = self.end_time - self.start_time

        # psutil restituisce i byte, dividiamo per (1024*1024) per avere i MegaByte
        self.ram_delta_mb = (self.end_ram - self.start_ram) / (1024 * 1024)

        # Estraiamo i kWh e convertiamo i kg di CO2 in grammi per maggiore leggibilità
        self.energy_kwh = self.tracker._total_energy.kWh
        self.co2_g = co2_kg * 1000