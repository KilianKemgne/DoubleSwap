import time
import psutil
import matplotlib.pyplot as plt
from datetime import datetime
import subprocess
import threading

interval = 0.01
duration = 7200
redis_process_name = "redis-server"
redis_port = 6379

timestamps = []
app_timestamps = []
perf_timestamps = []
cpu_usage = []
cpu_usage_cpu2 = []
memory_usage = []
app_memory_usage = [] 
disk_io_read = []
disk_io_write = []
children_data = {}

def load_data_from_files():
    # Charger les données CPU du parent
    with open('cpu_usage_cpu2.txt', 'r') as cpu2_file:
        for line in cpu2_file:
            timestamp_str, cpu2_str = line.strip().split(': ')
            timestamp = datetime.strptime(timestamp_str, '%H:%M:%S.%f')
            cpu_usage_cpu2.append(float(cpu2_str))
            perf_timestamps.append(timestamp)

    # Charger les données mémoire
    with open('memory_usage.txt', 'r') as memory_file:
        for line in memory_file:
            timestamp_str, memory_str = line.strip().split(': ')
            timestamp = datetime.strptime(timestamp_str, '%H:%M:%S.%f')
            memory_usage.append(float(memory_str))
            timestamps.append(timestamp)

    with open('app_memory_usage.txt', 'r') as app_memory_file:
        for line in app_memory_file:
            timestamp_str, app_memory_str = line.strip().split(': ')
            timestamp = datetime.strptime(timestamp_str, '%H:%M:%S.%f')
            app_memory_usage.append(float(app_memory_str))
            app_timestamps.append(timestamp)

    # Charger les données de lecture disque
    with open('disk_io_read.txt', 'r') as disk_read_file:
        for line in disk_read_file:
            timestamp_str, read_str = line.strip().split(': ')
            timestamp = datetime.strptime(timestamp_str, '%H:%M:%S.%f')
            disk_io_read.append(float(read_str))

    # Charger les données d'écriture disque
    # with open('disk_io_write.txt', 'r') as disk_write_file:
    #     for line in disk_write_file:
    #         timestamp_str, write_str = line.strip().split(': ')
    #         timestamp = datetime.strptime(timestamp_str, '%H:%M:%S.%f')
    #         disk_io_write.append(float(write_str))

    # Charger les données des processus enfants
    for pid in [419847, 427647]:
        children_data[pid] = {'timestamps': [], 'memory_usage': [], 'disk_io_read': [], 'disk_io_write': [], 'cpu_usage_perf': []}
        with open(f'child_{pid}_disk_io_read.txt', 'r') as child_disk_read_file:
            for line in child_disk_read_file:
                timestamp_str, read_str = line.strip().split(': ')
                timestamp = datetime.strptime(timestamp_str, '%H:%M:%S.%f')
                children_data[pid]['disk_io_read'].append(float(read_str))
                children_data[pid]['timestamps'].append(timestamp)

        with open(f'child_{pid}_memory_usage.txt', 'r') as child_memory_usage_file:
            for line in child_memory_usage_file:
                timestamp_str, memory_str = line.strip().split(': ')
                timestamp = datetime.strptime(timestamp_str, '%H:%M:%S.%f')
                children_data[pid]['memory_usage'].append(float(memory_str))

        with open(f'child_{pid}_cpu_usage_perf.txt', 'r') as child_cpu_perf_file:
            for line in child_cpu_perf_file:
                timestamp_str, cpu_str = line.strip().split(': ')
                timestamp = datetime.strptime(timestamp_str, '%H:%M:%S.%f')
                children_data[pid]['cpu_usage_perf'].append(float(cpu_str))

def plot_data():
    start_time = timestamps[0]
    time_in_minutes = [(t - start_time).total_seconds() / 60 for t in timestamps]

    # Zones pour les graphiques
    # zones = [
    #     (0, 10, 'Loading', 'lightblue'),
    #     (10, 20, 'Pause', 'lightgray'),
    #     (20, 53, 'Dump', 'lightgreen'),
    #     (53, 60, 'Pause', 'lightgray'),
    #     (60, 120, 'Perturbation', 'lightcoral'),
    #     (120, 129, 'Pause', 'lightgray'),
    #     (129, 325, 'Dump (Double Swap)', 'lightgreen')
    # ]
    zones = [
        (0, 10, 'Loading', 'lightblue'),
        (10, 20, 'Pause', 'lightgray'),
        (20, 46, 'Dump', 'lightgreen'),
        (46, 55, 'Pause', 'lightgray'),
        (55, 97, 'Perturbation', 'lightcoral'),
        (97, 105, 'Pause', 'lightgray'),
        (105, 250, 'Dump (Double Swap)', 'lightgreen')
    ]

    def add_zones():
        for start, end, label, color in zones:
            plt.axvspan(start / 60, end / 60, color=color, alpha=0.3, label=label)

    time_in_minutes_mem = [(t - start_time).total_seconds() / 60 for t in timestamps[:len(memory_usage)]]
    time_in_minutes_app_mem = [(t - start_time).total_seconds() / 60 for t in app_timestamps[:len(app_memory_usage)]]
     # Figure 1 : Memory Usage (Redis, App et enfants de Redis)
    plt.figure(figsize=(12, 6))
    plt.plot(time_in_minutes_mem, memory_usage, label='Memory Usage Redis (MB)', color='blue')
    plt.plot(time_in_minutes_app_mem, app_memory_usage, label='Memory Usage Disturber (MB)', color='red', linestyle='--')
    for pid, data in children_data.items():
        time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps']]
        plt.plot(time_in_minutes_child, data['memory_usage'], label=f'Memory Usage (Child PID={pid}, MB)', linestyle=':', color='green')
    # Ajouter une ligne horizontale pour indiquer la mémoire totale de la machine (16 Go)
    total_memory_gb = 16  # Mémoire totale de la machine en Go
    total_memory_mb = total_memory_gb * 1024  # Convertir en Mo
    plt.axhline(y=total_memory_mb, color='black', linestyle='--', linewidth=1, label=f'Total Memory ({total_memory_gb} Go)')
    
    # Ajuster l'axe des ordonnées pour qu'il aille jusqu'à 16 Go
    # plt.ylim(0, total_memory_mb)  # Limite de l'axe des ordonnées jusqu'à 16 Go (en Mo)
    add_zones()
    plt.xlabel('Time (minutes)')
    plt.ylabel('Memory Usage (MB)')
    plt.title('Memory Usage by Redis, Disturber, and Redis Children')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('memory_usage_redis_app_children.png')

    time_in_minutes_io = [(t - start_time).total_seconds() / 60 for t in timestamps[:len(disk_io_read)]]
    # Figure 2 : Disk I/O (Parent and Children)
    plt.figure(figsize=(12, 6))
    plt.plot(time_in_minutes_io, disk_io_read, label='Disk Read (Parent, MB)', color='blue')
    for pid, data in children_data.items():
        time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps']]
        plt.plot(time_in_minutes_child, data['disk_io_read'], label=f'Disk Read (Child PID={pid}, MB)', linestyle='--', color='green')
    add_zones()
    plt.xlabel('Time (minutes)')
    plt.ylabel('Disk IO (MB)')
    plt.title('Disk Activity by Redis')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('redis_disk_io_with_children.png')

    # Figure 1 : CPU Usage (Parent and Children via perf)
    plt.figure(figsize=(12, 6))
    time_in_minutes_truncated = [(t - perf_timestamps[0]).total_seconds() / 60 for t in perf_timestamps]
    plt.plot(time_in_minutes_truncated, cpu_usage_cpu2, label='CPU Usage (Parent, %)', color='blue')
    for pid, data in children_data.items():
        time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps'][:len(data['cpu_usage_perf'])]]
        plt.plot(time_in_minutes_child, data['cpu_usage_perf'], label=f'CPU Usage (Child PID={pid}, %)', color='green')
    add_zones()
    plt.xlabel('Time (minutes)')
    plt.ylabel('CPU Usage (%)')
    plt.title('CPU Usage by Redis')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('redis_cpu_usage_with_children_perf.png')

if __name__ == "__main__":
    try:
        print("Chargement des données à partir des fichiers...")
        load_data_from_files()

        print("Tracé des courbes...")
        plot_data()

    except Exception as e:
        print(f"Erreur : {e}")