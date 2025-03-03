import time
import psutil
import matplotlib.pyplot as plt
from datetime import datetime

# Configuration
interval = 0.001  # Intervalle de collecte en secondes (1 ms)
duration = 10  # Durée totale de collecte en secondes
redis_process_name = "redis-server"  # Nom du processus Redis

# Variables pour stocker les données
timestamps = []
cpu_usage = []
memory_usage = []
disk_io_read = []
disk_io_write = []

# Trouver le processus Redis
def find_redis_process():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == redis_process_name:
            return proc
    raise Exception(f"Processus '{redis_process_name}' introuvable.")

# Collecte des données
def collect_data(proc, interval, duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        # Temps actuel
        timestamps.append(datetime.now())

        # Utilisation du CPU
        cpu_usage.append(proc.cpu_percent(interval=interval))

        # Utilisation de la mémoire
        memory_usage.append(proc.memory_info().rss / (1024 * 1024))  # en Mo

        # Activité disque
        disk_io = proc.io_counters()
        disk_io_read.append(disk_io.read_bytes / (1024 * 1024))  # en Mo
        disk_io_write.append(disk_io.write_bytes / (1024 * 1024))  # en Mo

        # Attendre jusqu'au prochain intervalle
        time.sleep(interval)

# Tracer les courbes
def plot_data():
    plt.figure(figsize=(12, 8))

    # Courbe CPU
    plt.subplot(3, 1, 1)
    plt.plot(timestamps, cpu_usage, label='CPU Usage (%)', color='blue')
    plt.xlabel('Temps')
    plt.ylabel('CPU Usage (%)')
    plt.title('Utilisation du CPU par Redis')
    plt.legend()

    # Courbe Mémoire
    plt.subplot(3, 1, 2)
    plt.plot(timestamps, memory_usage, label='Memory Usage (Mo)', color='green')
    plt.xlabel('Temps')
    plt.ylabel('Memory Usage (Mo)')
    plt.title('Utilisation de la mémoire par Redis')
    plt.legend()

    # Courbe Disque
    plt.subplot(3, 1, 3)
    plt.plot(timestamps, disk_io_read, label='Disk Read (Mo)', color='red')
    plt.plot(timestamps, disk_io_write, label='Disk Write (Mo)', color='orange')
    plt.xlabel('Temps')
    plt.ylabel('Disk IO (Mo)')
    plt.title('Activité disque par Redis')
    plt.legend()

    plt.tight_layout()
    plt.show()

# Point d'entrée du script
if __name__ == "__main__":
    try:
        # Trouver le processus Redis
        redis_proc = find_redis_process()

        # Collecter les données
        print(f"Collecte des données pendant {duration} secondes...")
        collect_data(redis_proc, interval, duration)

        # Tracer les courbes
        print("Tracé des courbes...")
        plot_data()

    except Exception as e:
        print(f"Erreur : {e}")
