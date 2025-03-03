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
perf_timestamps = []
cpu_usage = []
cpu_usage_cpu2 = []
memory_usage = []
disk_io_read = []
disk_io_write = []
children_data = {}

def find_redis_process():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == redis_process_name:
            return proc
    return None

def is_redis_running(proc):
    try:
        return proc.is_running()
    except psutil.NoSuchProcess:
        return False

def collect_data(proc, interval, duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        if not is_redis_running(proc):
            print("Le processus Redis n'est plus en cours d'exécution. Arrêt de la collecte...")
            break

        current_time = datetime.now()
        timestamps.append(current_time)

        cpu_usage.append(proc.cpu_percent(interval=interval))

        memory_usage.append(proc.memory_info().rss / (1024 * 1024))

        disk_io = proc.io_counters()
        disk_io_read.append(disk_io.read_bytes / (1024 * 1024))
        disk_io_write.append(disk_io.write_bytes / (1024 * 1024))

        time.sleep(interval)

def collect_perf_data_for_child(pid, interval, duration, data_list):
    # start_time = time.time()
    # while time.time() - start_time < duration:
    if not psutil.pid_exists(pid):
        print(f"Le processus {pid} n'est plus en cours d'exécution. Arrêt de la collecte perf...")
        return

    command = f"perf stat -p {pid} -e cpu-clock sleep {interval} > perf_temp_child.txt 2>&1"
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError:
        print("Échec de l'exécution de la commande perf. Sortie de la fonction.")
        return

    with open("perf_temp_child.txt", "r") as file:
        lines = file.readlines()
        for line in lines:
            if "CPUs utilized" in line:
                parts = line.split()
                cpu_utilized_index = parts.index("CPUs") - 1
                
                try:
                    cpu_utilized = float(parts[cpu_utilized_index].replace(",", "."))
                    cpu_utilized_percent = cpu_utilized * 100
                    data_list.append(cpu_utilized_percent)
                except ValueError:
                    # print(f"Valeur invalide pour CPU utilisé: {parts[cpu_utilized_index]}. Ignorée.")
                    print(".")
                break

def collect_child_data(proc, interval, duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        if not is_redis_running(proc):
            print("Le processus Redis n'est plus en cours d'exécution. Arrêt de la collecte des enfants...")
            break

        children = proc.children()
        for child in children:
            if child.pid not in children_data:
                children_data[child.pid] = {'timestamps': [], 'cpu_usage': [], 'disk_io_read': [], 'disk_io_write': [], 'cpu_usage_perf': []}

            current_time = datetime.now()
            children_data[child.pid]['timestamps'].append(current_time)
            # children_data[child.pid]['cpu_usage'].append(child.cpu_percent(interval=interval))
            disk_io = child.io_counters()
            children_data[child.pid]['disk_io_read'].append(disk_io.read_bytes / (1024 * 1024))  # en Mo
            children_data[child.pid]['disk_io_write'].append(disk_io.write_bytes / (1024 * 1024))  # en Mo

            collect_perf_data_for_child(child.pid, interval, duration, children_data[child.pid]['cpu_usage_perf'])

        time.sleep(interval)

def save_data_to_files():
    # with open('cpu_usage.txt', 'w') as cpu_file:
    #     for timestamp, cpu in zip(timestamps, cpu_usage):
    #         cpu_file.write(f"{timestamp.strftime('%H:%M')}: {cpu}\n")

    with open('cpu_usage_cpu2.txt', 'w') as cpu2_file:
        for timestamp, cpu2 in zip(perf_timestamps, cpu_usage_cpu2):
            cpu2_file.write(f"{timestamp.strftime('%H:%M')}: {cpu2}\n")

    with open('memory_usage.txt', 'w') as memory_file:
        for timestamp, memory in zip(timestamps, memory_usage):
            memory_file.write(f"{timestamp.strftime('%H:%M')}: {memory}\n")

    with open('disk_io_read.txt', 'w') as disk_read_file:
        for timestamp, read in zip(timestamps, disk_io_read):
            disk_read_file.write(f"{timestamp.strftime('%H:%M')}: {read}\n")

    with open('disk_io_write.txt', 'w') as disk_write_file:
        for timestamp, write in zip(timestamps, disk_io_write):
            disk_write_file.write(f"{timestamp.strftime('%H:%M')}: {write}\n")

    for pid, data in children_data.items():
        # with open(f'child_{pid}_cpu_usage.txt', 'w') as child_cpu_file:
        #     for timestamp, cpu in zip(data['timestamps'], data['cpu_usage']):
        #         child_cpu_file.write(f"{timestamp.strftime('%H:%M')}: {cpu}\n")

        with open(f'child_{pid}_disk_io_read.txt', 'w') as child_disk_read_file:
            for timestamp, read in zip(data['timestamps'], data['disk_io_read']):
                child_disk_read_file.write(f"{timestamp.strftime('%H:%M')}: {read}\n")

        with open(f'child_{pid}_disk_io_write.txt', 'w') as child_disk_write_file:
            for timestamp, write in zip(data['timestamps'], data['disk_io_write']):
                child_disk_write_file.write(f"{timestamp.strftime('%H:%M')}: {write}\n")

        with open(f'child_{pid}_cpu_usage_perf.txt', 'w') as child_cpu_perf_file:
            for timestamp, cpu in zip(data['timestamps'], data['cpu_usage_perf']):
                child_cpu_perf_file.write(f"{timestamp.strftime('%H:%M')}: {cpu}\n")

def plot_data():
    start_time = timestamps[0]
    time_in_minutes = [(t - start_time).total_seconds() / 60 for t in timestamps[:len(memory_usage)]]

    # with SSD
    # zones = [
    #     (0, 20, 'Loading', 'lightblue'),
    #     (20, 30, 'Pause', 'lightgray'),
    #     (30, 102, 'Dump', 'lightgreen'),
    #     (102, 220, 'Perturbation', 'lightcoral'),
    #     # (110, 330, 'Perturbation', 'lightcoral'),
    #     # (330, 340, 'Pause', 'lightgray'),
    #     (220, time_in_minutes[-1], 'Double Swap', 'lightyellow')
    # ]

    # with HDD
    zones = [
        (0, 20, 'Loading', 'lightblue'),
        (20, 30, 'Pause', 'lightgray'),
        (30, 102, 'Dump', 'lightgreen'),
        (102, 432, 'Perturbation', 'lightcoral'),
        # (110, 330, 'Perturbation', 'lightcoral'),
        # (330, 340, 'Pause', 'lightgray'),
        (432, time_in_minutes[-1], 'Double Swap', 'lightyellow')
    ]

    def add_zones():
        for start, end, label, color in zones:
            plt.axvspan(start / 60, end / 60, color=color, alpha=0.3, label=label)
            # plt.axvline(x=start / 60, color='black', linestyle='--', linewidth=0.5)
            # plt.axvline(x=end / 60, color='black', linestyle='--', linewidth=0.5)
            # plt.text((start + end) / 120, plt.ylim()[1] * 0.95, f'{start}s - {end}s', 
            #          rotation=90, fontsize=8, color='black', ha='center', va='top')


    # Figure 3 : Memory Usage
    plt.figure(figsize=(12, 6))
    plt.plot(time_in_minutes, memory_usage, label='Memory Usage (MB)', color='green')
    add_zones()
    plt.xlabel('Time (minutes)')
    plt.ylabel('Memory Usage (MB)')
    plt.title('Memory Usage by Redis')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('redis_memory_usage.png')
    plt.show()

    time_in_minutes_io = [(t - start_time).total_seconds() / 60 for t in timestamps[:len(disk_io_read)]]
    # Figure 2 : Disk I/O (Parent and Children)
    plt.figure(figsize=(12, 6))
    plt.plot(time_in_minutes_io, disk_io_read, label='Disk Read (Parent, MB)', color='red')
    plt.plot(time_in_minutes_io, disk_io_write, label='Disk Write (Parent, MB)', color='orange')
    for pid, data in children_data.items():
        time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps']]
        plt.plot(time_in_minutes_child, data['disk_io_read'], label=f'Disk Read (Child PID={pid}, MB)', linestyle='--')
        plt.plot(time_in_minutes_child, data['disk_io_write'], label=f'Disk Write (Child PID={pid}, MB)', linestyle='--')
    add_zones()
    plt.xlabel('Time (minutes)')
    plt.ylabel('Disk IO (MB)')
    plt.title('Disk Activity by Redis')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('redis_disk_io_with_children.png')
    plt.show()

    # Figure 1 : CPU Usage (Parent and Children via perf)
    plt.figure(figsize=(12, 6))
    time_in_minutes_truncated = [(t - perf_timestamps[0]).total_seconds() / 60 for t in perf_timestamps]
    plt.plot(time_in_minutes_truncated, cpu_usage_cpu2, label='CPU Usage (Parent, %)', color='blue')
    for pid, data in children_data.items():
        time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps'][:len(data['cpu_usage_perf'])]]
        plt.plot(time_in_minutes_child, data['cpu_usage_perf'], label=f'CPU Usage (Child PID={pid}, %)', color='red')
    add_zones()
    plt.xlabel('Time (minutes)')
    plt.ylabel('CPU Usage (%)')
    plt.title('CPU Usage by Redis')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('redis_cpu_usage_with_children_perf.png')
    plt.show()
    

    # Figure 1 : Utilisation du CPU (parent et enfants)
    # plt.figure(figsize=(12, 6))
    # plt.plot(time_in_minutes, cpu_usage, label='CPU Usage (Parent, %)', color='blue')
    # for pid, data in children_data.items():
    #     time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps']]
    #     plt.plot(time_in_minutes_child, data['cpu_usage'], label=f'CPU Usage (Child PID={pid}, %)', linestyle='--')
    # plt.xlabel('Temps (minutes)')
    # plt.ylabel('CPU Usage (%)')
    # plt.title('Utilisation du CPU par Redis (Parent et Enfants)')
    # plt.legend(loc="upper right")
    # plt.xticks(range(int(time_in_minutes[-1]) + 1))
    # plt.tight_layout()
    # plt.savefig('redis_cpu_usage_with_children.png')
    # plt.show()

    # Figure 4 : Activité réseau (parent)
    # plt.figure(figsize=(12, 6))
    # plt.plot(time_in_minutes, network_io_sent, label='Network Sent (Parent, Mo)', color='cyan')
    # plt.plot(time_in_minutes, network_io_recv, label='Network Received (Parent, Mo)', color='magenta')
    # plt.xlabel('Temps (minutes)')
    # plt.ylabel('Network IO (Mo)')
    # plt.title('Activité réseau sur le port Redis (Parent)')
    # plt.legend(loc="upper right")
    # plt.xticks(range(int(time_in_minutes[-1]) + 1))
    # plt.tight_layout()
    # plt.savefig('redis_network_io.png')
    # plt.show()

def collect_perf_data(pid, interval, duration, data_list):
    start_time = time.time()
    while time.time() - start_time < duration:
        if not psutil.pid_exists(pid):
            print(f"Le processus {pid} n'est plus en cours d'exécution. Arrêt de la collecte perf...")
            break

        command = f"perf stat -p {pid} -e cpu-clock sleep {interval} > perf_temp.txt 2>&1"
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError:
            print("Échec de l'exécution de la commande perf. Sortie de la fonction.")
            save_data_to_files()
            plot_data()
            return

        with open("perf_temp.txt", "r") as file:
            lines = file.readlines()
            for line in lines:
                if "CPUs utilized" in line:
                    perf_timestamps.append(datetime.now())
                    parts = line.split()
                    cpu_utilized_index = parts.index("CPUs") - 1
                    
                    try:
                        cpu_utilized = float(parts[cpu_utilized_index].replace(",", "."))
                        cpu_utilized_percent = cpu_utilized * 100
                        data_list.append(cpu_utilized_percent)
                    except ValueError:
                        # print(f"Valeur invalide pour CPU utilisé: {parts[cpu_utilized_index]}. Ignorée.")
                        if perf_timestamps:
                            perf_timestamps.pop()
                        print(".")
                    break


if __name__ == "__main__":
    try:
        redis_proc = find_redis_process()
        if not redis_proc:
            raise Exception(f"Processus '{redis_process_name}' introuvable.")
        print(f"Processus Redis trouvé (PID={redis_proc.pid}).")

        print("Démarrage de la collecte des données CPU sur le CPU 2 avec perf...")
        perf_thread = threading.Thread(target=collect_perf_data, args=(redis_proc.pid, interval, duration, cpu_usage_cpu2))
        perf_thread.start()

        print("Démarrage de la collecte des données pour les processus enfants...")
        child_thread = threading.Thread(target=collect_child_data, args=(redis_proc, interval, duration))
        child_thread.start()

        print(f"Collecte des données pendant {duration} secondes...")
        collect_data(redis_proc, interval, duration)

        perf_thread.join()
        child_thread.join()

        print("Sauvegarde des données dans des fichiers...")
        save_data_to_files()

        print("Tracé des courbes...")
        plot_data()

    except Exception as e:
        print(f"Erreur : {e}")
