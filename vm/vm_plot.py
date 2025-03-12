import time
import psutil
import matplotlib.pyplot as plt
from datetime import datetime
import subprocess
import threading

interval = 0.01
duration = 7200
vm_process_name = "qemu-system-x86_64"
app_process_name = "app"  # Remplacez par le nom du processus de votre application

timestamps = []
perf_timestamps = []
cpu_usage = []
cpu_usage_cpu2 = []
memory_usage = []
app_memory_usage = []  # Pour stocker l'utilisation mémoire de l'application `app`
disk_io_read = []
disk_io_write = []
children_data = {}

def find_process(process_name):
    """Trouve un processus par son nom."""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc
    return None

def is_process_running(proc):
    """Vérifie si un processus est en cours d'exécution."""
    try:
        return proc.is_running()
    except psutil.NoSuchProcess:
        return False

def collect_data(vm_proc, interval, duration):
    """Collecte les données pour vm, ses enfants et l'application `app`."""
    start_time = time.time()
    app_proc = None  # Initialisation du processus de l'application `app`
    app_start_time = None  # Temps de démarrage de l'application `app`

    while time.time() - start_time < duration:
        current_time = datetime.now()
        timestamps.append(current_time)

        # Collecter les données pour vm
        if is_process_running(vm_proc):
            cpu_usage.append(vm_proc.cpu_percent(interval=interval))
            memory_usage.append(vm_proc.memory_info().rss / (1024 * 1024))  # en Mo
            disk_io = vm_proc.io_counters()
            disk_io_read.append(disk_io.read_bytes / (1024 * 1024))  # en Mo
            disk_io_write.append(disk_io.write_bytes / (1024 * 1024))  # en Mo
        else:
            print("Le processus vm n'est plus en cours d'exécution. Arrêt de la collecte...")
            break

        # Vérifier si l'application `app` est lancée
        if app_proc is None:
            app_proc = find_process(app_process_name)
            if app_proc:
                app_start_time = time.time()  # Enregistrer le temps de démarrage de l'application `app`
                print(f"Processus {app_process_name} trouvé (PID={app_proc.pid}). Début de la collecte des données.")

        # Collecter les données pour l'application `app` si elle est en cours d'exécution
        if app_proc and is_process_running(app_proc):
            app_memory_usage.append(app_proc.memory_info().rss / (1024 * 1024))  # en Mo
        else:
            app_memory_usage.append(0)  # Si l'application n'est pas en cours d'exécution

        time.sleep(interval)

def collect_perf_data_for_child(pid, interval, duration, data_list):
    """Collecte les données de performance pour un processus enfant."""
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
                    print(".")
                break

def collect_child_data(vm_proc, interval, duration):
    """Collecte les données pour les processus enfants de vm."""
    start_time = time.time()
    while time.time() - start_time < duration:
        if not is_process_running(vm_proc):
            print("Le processus vm n'est plus en cours d'exécution. Arrêt de la collecte des enfants...")
            break

        children = vm_proc.children()
        for child in children:
            if child.pid not in children_data:
                children_data[child.pid] = {'timestamps': [], 'memory_usage': [], 'disk_io_read': [], 'disk_io_write': [], 'cpu_usage_perf': []}

            current_time = datetime.now()
            children_data[child.pid]['timestamps'].append(current_time)
            children_data[child.pid]['memory_usage'].append(child.memory_info().rss / (1024 * 1024))  # en Mo
            disk_io = child.io_counters()
            children_data[child.pid]['disk_io_read'].append(disk_io.read_bytes / (1024 * 1024))  # en Mo
            children_data[child.pid]['disk_io_write'].append(disk_io.write_bytes / (1024 * 1024))  # en Mo

            collect_perf_data_for_child(child.pid, interval, duration, children_data[child.pid]['cpu_usage_perf'])

        time.sleep(interval)

def save_data_to_files():
    """Sauvegarde les données collectées dans des fichiers."""
    with open('cpu_usage_cpu2.txt', 'w') as cpu2_file:
        for timestamp, cpu2 in zip(perf_timestamps, cpu_usage_cpu2):
            cpu2_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {cpu2}\n")

    with open('memory_usage.txt', 'w') as memory_file:
        for timestamp, memory in zip(timestamps, memory_usage):
            memory_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {memory}\n")

    with open('app_memory_usage.txt', 'w') as app_memory_file:
        for timestamp, memory in zip(timestamps, app_memory_usage):
            app_memory_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {memory}\n")

    with open('disk_io_read.txt', 'w') as disk_read_file:
        for timestamp, read in zip(timestamps, disk_io_read):
            disk_read_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {read}\n")

    with open('disk_io_write.txt', 'w') as disk_write_file:
        for timestamp, write in zip(timestamps, disk_io_write):
            disk_write_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {write}\n")

    for pid, data in children_data.items():
        with open(f'child_{pid}_memory_usage.txt', 'w') as child_memory_file:
            for timestamp, memory in zip(data['timestamps'], data['memory_usage']):
                child_memory_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {memory}\n")

        with open(f'child_{pid}_disk_io_read.txt', 'w') as child_disk_read_file:
            for timestamp, read in zip(data['timestamps'], data['disk_io_read']):
                child_disk_read_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {read}\n")

        with open(f'child_{pid}_disk_io_write.txt', 'w') as child_disk_write_file:
            for timestamp, write in zip(data['timestamps'], data['disk_io_write']):
                child_disk_write_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {write}\n")

        with open(f'child_{pid}_cpu_usage_perf.txt', 'w') as child_cpu_perf_file:
            for timestamp, cpu in zip(data['timestamps'], data['cpu_usage_perf']):
                child_cpu_perf_file.write(f"{timestamp.strftime('%H:%M:%S.%f')}: {cpu}\n")

def plot_data():
    """Trace les graphiques pour vm, ses enfants et l'application `app`."""
    start_time = timestamps[0]
    time_in_minutes = [(t - start_time).total_seconds() / 60 for t in timestamps]

    # Zones pour les graphiques
    zones = [
        (0, 10, 'Loading', 'lightblue'),
        (10, 20, 'Pause', 'lightgray'),
        (20, 50, 'Dump', 'lightgreen'),
        (50, 60, 'Pause', 'lightgray'),
        (60, 46, 'Perturbation', 'lightcoral'),
        (46, 56, 'Pause', 'lightgray'),
        (56, max(time_in_minutes), 'Double Swap', 'lightyellow')
    ]

    def add_zones():
        for start, end, label, color in zones:
            plt.axvspan(start / 60, end / 60, color=color, alpha=0.3, label=label)

    # Figure 1 : Memory Usage (vm, App et enfants de vm)
    plt.figure(figsize=(12, 6))
    plt.plot(time_in_minutes[:len(memory_usage)], memory_usage, label='Memory Usage VM (MB)', color='blue')
    plt.plot(time_in_minutes[:len(app_memory_usage)], app_memory_usage, label='Memory Usage Disturber (MB)', color='red', linestyle='--')
    for pid, data in children_data.items():
        time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps']]
        plt.plot(time_in_minutes_child, data['memory_usage'], label=f'Memory Usage (Child PID={pid}, MB)', linestyle=':', color='green')
    add_zones()
    plt.xlabel('Time (minutes)')
    plt.ylabel('Memory Usage (MB)')
    plt.title('Memory Usage by VM, App, and vm Children')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('memory_usage_vm_app_children.png')

    time_in_minutes_io = [(t - start_time).total_seconds() / 60 for t in timestamps[:len(disk_io_read)]]
    # Figure 2 : Disk I/O (Parent and Children)
    plt.figure(figsize=(12, 6))
    plt.plot(time_in_minutes_io, disk_io_read, label='Disk Read (Parent, MB)', color='blue')
    # plt.plot(time_in_minutes_io, disk_io_write, label='Disk Write (Parent, MB)', color='orange')
    for pid, data in children_data.items():
        time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps']]
        plt.plot(time_in_minutes_child, data['disk_io_read'], label=f'Disk Read (Child PID={pid}, MB)', linestyle='--')
        # plt.plot(time_in_minutes_child, data['disk_io_write'], label=f'Disk Write (Child PID={pid}, MB)', linestyle='--')
    add_zones()
    plt.xlabel('Time (minutes)')
    plt.ylabel('Disk IO (MB)')
    plt.title('Disk Activity by VM')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('vm_disk_io_with_children.png')
    # plt.show()

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
    plt.title('CPU Usage by VM')
    plt.legend(loc="upper right")
    plt.xticks(range(int(time_in_minutes[-1]) + 1))
    plt.tight_layout()
    plt.savefig('vm_cpu_usage_with_children_perf.png')
    # plt.show()
    

    # Figure 1 : Utilisation du CPU (parent et enfants)
    # plt.figure(figsize=(12, 6))
    # plt.plot(time_in_minutes, cpu_usage, label='CPU Usage (Parent, %)', color='blue')
    # for pid, data in children_data.items():
    #     time_in_minutes_child = [(t - start_time).total_seconds() / 60 for t in data['timestamps']]
    #     plt.plot(time_in_minutes_child, data['cpu_usage'], label=f'CPU Usage (Child PID={pid}, %)', linestyle='--')
    # plt.xlabel('Temps (minutes)')
    # plt.ylabel('CPU Usage (%)')
    # plt.title('Utilisation du CPU par vm (Parent et Enfants)')
    # plt.legend(loc="upper right")
    # plt.xticks(range(int(time_in_minutes[-1]) + 1))
    # plt.tight_layout()
    # plt.savefig('vm_cpu_usage_with_children.png')
    # plt.show()

    # Figure 4 : Activité réseau (parent)
    # plt.figure(figsize=(12, 6))
    # plt.plot(time_in_minutes, network_io_sent, label='Network Sent (Parent, Mo)', color='cyan')
    # plt.plot(time_in_minutes, network_io_recv, label='Network Received (Parent, Mo)', color='magenta')
    # plt.xlabel('Temps (minutes)')
    # plt.ylabel('Network IO (Mo)')
    # plt.title('Activité réseau sur le port vm (Parent)')
    # plt.legend(loc="upper right")
    # plt.xticks(range(int(time_in_minutes[-1]) + 1))
    # plt.tight_layout()
    # plt.savefig('vm_network_io.png')
    # plt.show()

def collect_perf_data(pid, interval, duration, data_list):
    start_time = time.time()
    while time.time() - start_time < duration:
        if not psutil.pid_exists(pid):
            print(f"Le processus {pid} n'est plus en cours d'exécution. Arrêt de la collecte perf...")
            save_data_to_files()
            plot_data()
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
        vm_proc = find_process(vm_process_name)
        if not vm_proc:
            raise Exception(f"Processus '{vm_process_name}' introuvable.")
        print(f"Processus vm trouvé (PID={vm_proc.pid}).")

        print("Démarrage de la collecte des données CPU sur le CPU 2 avec perf...")
        perf_thread = threading.Thread(target=collect_perf_data, args=(vm_proc.pid, interval, duration, cpu_usage_cpu2))
        perf_thread.start()

        print("Démarrage de la collecte des données pour les processus enfants...")
        child_thread = threading.Thread(target=collect_child_data, args=(vm_proc, interval, duration))
        child_thread.start()

        print(f"Collecte des données pendant {duration} secondes...")
        collect_data(vm_proc, interval, duration)

        perf_thread.join()
        child_thread.join()

        print("Sauvegarde des données dans des fichiers...")
        save_data_to_files()

        print("Tracé des courbes...")
        plot_data()

    except Exception as e:
        print(f"Erreur : {e}")
