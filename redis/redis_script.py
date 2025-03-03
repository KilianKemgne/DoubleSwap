from collections import defaultdict
import re

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


def merge_and_sort_files():
    data_by_pfn = defaultdict(list)
    sequence_count = 0
    sequence_cache = 0
    sequence_wp = 0

    try:
        with open("/usr/vm/data/guest_data.txt", "rt") as file:
            lines = file.readlines()

        for line in lines:
            pfn, data_type, timestamp = parse_line_guest(line)
            if pfn is not None:
                data_by_pfn[pfn].append((timestamp, data_type))

    except FileNotFoundError:
        print("Failed to open /usr/vm/data/guest_data.txt.")
        return
    except Exception as e:
        print("An error occurred while reading guest_data.txt:", e)
        return

    try:
        with open("/usr/vm/data/data.txt", "rt") as file:
            lines = file.readlines()

        for line in lines:
            tokens = line.strip().split()
            if len(tokens) == 7 :
                pfn, data_type, timestamp, process_name, start_time = parse_line(line)
                if pfn is not None and timestamp and data_type:
                    data_by_pfn[pfn].append((timestamp, data_type))

    except FileNotFoundError:
        print("Failed to open /usr/vm/data/data.txt.")
        return
    except Exception as e:
        print("An error occurred while reading data.txt:", e)
        return

    try:
        with open("/usr/vm/data/data_in.txt", "rt") as file:
            lines = file.readlines()

        for line in lines:
            tokens = line.strip().split()
            if len(tokens) == 7 :
                pfn, data_type, timestamp, process_name, start_time = parse_line(line)
                if pfn is not None and timestamp and data_type:
                    data_by_pfn[pfn].append((timestamp, data_type))

    except FileNotFoundError:
        print("Failed to open /usr/vm/data/data_in.txt.")
        return
    except Exception as e:
        print("An error occurred while reading data_in.txt:", e)
        return
    
    try : 
         with open("/usr/vm/data/merged_data.txt", "wt") as outfile, open("/usr/vm/data/double_swap.txt", "wt") as outfile1:
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


merge_and_sort_files()

