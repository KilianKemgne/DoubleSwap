import ctypes
from collections import defaultdict
import re

class HostGuestPte(ctypes.Structure):
    pass  

HostGuestPte._fields_ = [
    ("userspace_addr", ctypes.c_ulong),
    ("guest_phys_addr", ctypes.c_ulong),
    ("size", ctypes.c_ulong),
    ("addr", ctypes.c_ulong),
    ("next", ctypes.POINTER(HostGuestPte))
]

hgpte = None

def get_hgpte():
    global hgpte
    if hgpte is not None:
        return hgpte

    try:
        with open("/tmp/hgfile.txt", "rt") as file:
            slot_count = 0
            entries = []

            for line in file:
                if slot_count >= 3:
                    break

                tokens = line.split()
                if len(tokens) < 4:
                    continue

                temp = HostGuestPte()
                temp.userspace_addr = int(tokens[0], 10)
                temp.guest_phys_addr = int(tokens[1], 10)
                temp.size = int(tokens[2], 10)
                temp.addr = int(tokens[3], 10)
                temp.next = None

                entries.append(temp)
                slot_count += 1

            entries.sort(key=lambda x: x.guest_phys_addr, reverse=True)

            hgpte = None
            current = None
            for entry in entries:
                if hgpte is None:
                    hgpte = entry
                else:
                    current.next = ctypes.pointer(entry)
                current = entry

    except FileNotFoundError:
        print("Failed to open file !!")
    except Exception as e:
        print("An error occurred:", e)

    return hgpte

def parse_line(line):
    tokens = line.strip().split()
    if len(tokens) < 7:
        return None, None, None, None, None

    pfn = int(tokens[0], 10)
    data_type = " ".join(tokens[1:4])
    timestamp = tokens[4]
    process_name = tokens[5]
    start_time = int(tokens[-1])

    return pfn, data_type, timestamp, process_name, start_time

def parse_line_guest(line):
    tokens = line.strip().split()
    if len(tokens) < 5:
        return None, None, None
    pfn = int(tokens[0], 10)
    data_type = " ".join(tokens[1:4])
    timestamp = tokens[4]

    return pfn, data_type, timestamp

def time_to_microseconds(timestamp):
    parts = timestamp.split(":")
    hours = int(parts[0]) * 3600 * 1_000_000
    minutes = int(parts[1]) * 60 * 1_000_000
    microseconds = int(parts[2])
    return hours + minutes + microseconds

def filter_qemu_process(lines):
    qemu_processes = {}

    for line in lines:
        _, _, _, process_name, start_time = parse_line(line)
        if process_name == "qemu-system-x86":
            if process_name not in qemu_processes or start_time < qemu_processes[process_name]:
                qemu_processes[process_name] = start_time

    if not qemu_processes:
        print("No qemu-system-x86 process found.")
        return None

    selected_start_time = min(qemu_processes.values())
    return selected_start_time


def contains_sequence(sorted_entries):
    pattern_groups = [
        [
            [r"OUT H NONE", r"OUT G.* NONE", r"IN H NONE", r"OUT G NONE"],
            [r"OUT H NONE", r"OUT G.* NONE", r"OUT G NONE", r"IN H NONE"],
            [r"OUT H NONE", r"IN H NONE", r"OUT G.* NONE", r"OUT G NONE"],
        ],
        [
            [r"OUT H NONE", r"OUT G.* NONE", r"IN H CACHE", r"OUT G NONE"],
            [r"OUT H NONE", r"OUT G.* NONE", r"OUT G NONE", r"IN H CACHE"],
            [r"OUT H NONE", r"IN H CACHE", r"OUT G.* NONE", r"OUT G NONE"]
        ],
        [
            [r"OUT H NONE", r"OUT G.* NONE", r"IN H WP", r"OUT G NONE"],
            [r"OUT H NONE", r"OUT G.* NONE", r"OUT G NONE", r"IN H WP"],
            [r"OUT H NONE", r"IN H WP", r"OUT G.* NONE", r"OUT G NONE"]
        ]
    ]

    for idx, group in enumerate(pattern_groups, start=1):
        for pattern_set in group:
            index = 0

            for _, remaining_data in sorted_entries:
                data_type = " ".join(remaining_data.split()[:3])

                if re.fullmatch(pattern_set[index], data_type):
                    index += 1

                    if index == len(pattern_set):
                        return idx

    return 0


# def contains_sequence(sorted_entries):
#     sequence = ["OUT H", "OUT G*", "IN H", "OUT G"]
#     # sequence = ["OUT G*", "IN H", "OUT G"]
#     pattern_cache = [
#         r"OUT H NONE",
#         r"OUT G.* NONE",
#         r"IN H CACHE",
#         r"OUT G NONE"
#     ]
#     pattern_cache2 = [
#         r"OUT H NONE",
#         r"OUT G.* NONE",
#         r"OUT G NONE",
#         r"IN H CACHE"
#     ]
#     pattern = [
#         r"OUT H NONE",
#         r"OUT G.* NONE",
#         r"IN H NONE",
#         r"OUT G NONE"
#     ]
#     pattern2 = [
#         r"OUT H NONE",
#         r"OUT G.* NONE",
#         r"OUT G NONE",
#         r"IN H NONE"
#     ]
#     pattern_wp = [
#         r"OUT H NONE",
#         r"OUT G.* NONE",
#         r"IN H WP",
#         r"OUT G NONE"
#     ]
#     pattern_wp2 = [
#         r"OUT H NONE",
#         r"OUT G.* NONE",
#         r"OUT G NONE",
#         r"IN H WP"
#     ]

#     index = 0
#     for _, remaining_data in sorted_entries:
#         data_type = " ".join(remaining_data.split()[:3])
#         if re.fullmatch(pattern_cache[index], data_type) or re.fullmatch(pattern_cache2[index], data_type):
#             index += 1
#             if index == len(sequence):
#                 return 1
#         if re.fullmatch(pattern[index], data_type) or re.fullmatch(pattern2[index], data_type):
#             index += 1
#             if index == len(sequence):
#                 return 2
#         if re.fullmatch(pattern_wp[index], data_type) or re.fullmatch(pattern_wp2[index], data_type):
#             index += 1
#             if index == len(sequence):
#                 return 3
#     return 0

def process_data_file():
    hgpte = get_hgpte()
    if hgpte is None:
        print("hgpte is not properly initialized.")
        return

    try:
        with open("/usr/data/guest_data.txt", "rt") as infile, open("/usr/data/temp_data.txt", "wt") as outfile:
            for line in infile:
                tokens = line.split()
                if len(tokens) < 1:
                    continue

                pfn = int(tokens[0], 10)
                pfn_value = pfn * 4096

                current = hgpte
                found = False
                while current is not None:
                    if pfn_value >= current.guest_phys_addr:
                        new_pfn = current.userspace_addr + (pfn_value - current.guest_phys_addr)
                        found = True
                        break
                    current = current.next.contents if current.next else None

                new_line = f"{new_pfn} " + " ".join(tokens[1:]) + "\n"
                outfile.write(new_line)

    except FileNotFoundError:
        print("Failed to open /usr/data/guest_data.txt.")
        return
    except Exception as e:
        print("An error occurred while processing the file:", e)
        return

def merge_and_sort_files():
    data_by_pfn = defaultdict(list)
    sequence_count = 0
    sequence_cache = 0
    sequence_wp = 0

    try:
        with open("/usr/data/temp_data.txt", "rt") as file:
            lines = file.readlines()

        for line in lines:
            pfn, data_type, timestamp = parse_line_guest(line)
            if pfn is not None:
                data_by_pfn[pfn].append((timestamp, data_type))

    except FileNotFoundError:
        print("Failed to open /usr/data/temp_data.txt.")
        return
    except Exception as e:
        print("An error occurred while reading temp_data.txt:", e)
        return

    try:
        with open("/usr/data/data.txt", "rt") as file:
            lines = file.readlines()

        selected_start_time = filter_qemu_process(lines)
        if selected_start_time is None:
            return

        for line in lines:
            tokens = line.strip().split()
            if len(tokens) == 7 :
                pfn, data_type, timestamp, process_name, start_time = parse_line(line)
                if pfn is not None and process_name == "qemu-system-x86" and start_time == selected_start_time and len(str(pfn)) == 15 and timestamp and data_type:
                    data_by_pfn[pfn].append((timestamp, data_type))

    except FileNotFoundError:
        print("Failed to open /usr/data/data.txt.")
        return
    except Exception as e:
        print("An error occurred while reading data.txt:", e)
        return

    try:
        with open("/usr/data/host_data.txt", "rt") as file:
            lines = file.readlines()

        selected_start_time = filter_qemu_process(lines)
        if selected_start_time is None:
            return

        for line in lines:
            tokens = line.strip().split()
            if len(tokens) == 7 :
                pfn, data_type, timestamp, process_name, start_time = parse_line(line)
                if pfn is not None and process_name == "qemu-system-x86" and start_time == selected_start_time and len(str(pfn)) == 15 and timestamp and data_type:
                    data_by_pfn[pfn].append((timestamp, data_type))

    except FileNotFoundError:
        print("Failed to open /usr/data/host_data.txt.")
        return
    except Exception as e:
        print("An error occurred while reading host_data.txt:", e)
        return

    try:
        with open("/usr/data/data_in.txt", "rt") as file:
            lines = file.readlines()

        selected_start_time = filter_qemu_process(lines)
        if selected_start_time is None:
            return

        for line in lines:
            tokens = line.strip().split()
            if len(tokens) == 7 :
                pfn, data_type, timestamp, process_name, start_time = parse_line(line)
                if pfn is not None and process_name == "qemu-system-x86" and start_time == selected_start_time and len(str(pfn)) == 15 and timestamp and data_type:
                    data_by_pfn[pfn].append((timestamp, data_type))

    except FileNotFoundError:
        print("Failed to open /usr/data/data_in.txt.")
        return
    except Exception as e:
        print("An error occurred while reading data_in.txt:", e)
        return
    
    try : 
         with open("/usr/data/merged_data.txt", "wt") as outfile, open("/usr/data/double_swap.txt", "wt") as outfile1:
            for pfn in sorted(data_by_pfn.keys()):
                sorted_entries = sorted(
                    data_by_pfn[pfn],
                    key=lambda x: time_to_microseconds(x[0])
                )

                match contains_sequence(sorted_entries):
                    case 1:
                        sequence_count += 1
                        for timestamp, data_type in sorted_entries:
                            outfile1.write(f"{pfn} {data_type} {timestamp}\n")
                    case 2:
                        sequence_cache += 1
                        for timestamp, data_type in sorted_entries:
                            outfile1.write(f"{pfn} {data_type} {timestamp}\n")
                    case 3:
                        sequence_wp += 1
                        for timestamp, data_type in sorted_entries:
                            outfile1.write(f"{pfn} {data_type} {timestamp}\n")
                if (len(sorted_entries) >= 4):
                    for timestamp, data_type in sorted_entries:
                        outfile.write(f"{pfn} {data_type} {timestamp}\n")

            print(f"\nTotal number of double swaps (host swap space): {sequence_count}")
            print(f"\nTotal number of double swaps (host swap cache): {sequence_cache}")
            print(f"\nTotal number of double swaps (host swap wp): {sequence_wp}")
            
    except Exception as e:
        print("An error occurred while writing merged_data.txt:", e)


process_data_file()
merge_and_sort_files()
