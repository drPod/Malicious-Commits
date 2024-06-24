import os
import csv
from collections import OrderedDict


def combine_and_deduplicate_csv(input_directory, output_file):
    all_lines = OrderedDict()
    total_lines = 0
    header = None

    # Read all CSV files in the input directory
    for filename in os.listdir(input_directory):
        if filename.endswith(".csv"):
            file_path = os.path.join(input_directory, filename)
            with open(file_path, "r", newline="") as csvfile:
                reader = csv.reader(csvfile)
                if header is None:
                    header = next(reader)  # Assume all files have the same header
                else:
                    next(reader)  # Skip header for subsequent files
                for row in reader:
                    line = ",".join(row)
                    if line not in all_lines:
                        all_lines[line] = 1
                    else:
                        all_lines[line] += 1
                    total_lines += 1

    # Sort lines by the numeric 'id' in the first column
    sorted_lines = sorted(all_lines.keys(), key=lambda x: int(x.split(",")[0]))

    # Write sorted unique lines to output file
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for line in sorted_lines:
            writer.writerow(line.split(","))

    unique_lines = len(all_lines)
    duplicates = total_lines - unique_lines

    return total_lines, unique_lines, duplicates


# Usage
input_directory = "files"
output_file = "combined_output.csv"

total_lines, unique_lines, duplicates = combine_and_deduplicate_csv(
    input_directory, output_file
)

print(f"Total lines processed: {total_lines}")
print(f"Unique lines after deduplication: {unique_lines}")
print(f"Number of duplicates removed: {duplicates}")
