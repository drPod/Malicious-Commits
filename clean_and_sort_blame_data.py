import csv
import os
from tqdm import tqdm


def clean_and_sort_csv(input_file, output_file):
    # Read the existing CSV
    with open(input_file, "r", newline="") as infile:
        reader = csv.reader(infile)
        header = next(reader)

        # Ensure we have at least 9 columns in the header
        if len(header) < 9:
            raise ValueError("Input CSV does not have enough columns")

        # Read all rows, filtering out those without 8th or 9th column
        rows = []
        for row in tqdm(reader, desc="Reading and filtering rows"):
            if len(row) >= 9 and row[7] and row[8]:
                rows.append(row)

        # Sort rows by the 'id' column (assuming it's the first column)
        rows.sort(key=lambda x: int(x[0]))

    # Write the sorted and filtered data to the output file
    with open(output_file, "w", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)

        for row in tqdm(rows, desc="Writing sorted rows"):
            writer.writerow(row)

    print(f"Cleaning and sorting complete. Results saved to {output_file}")
    print(f"Total rows in output: {len(rows)}")


if __name__ == "__main__":
    input_file = "commits_with_blame_data.csv"
    output_file = "commits_with_blame_data_cleaned_sorted.csv"
    clean_and_sort_csv(input_file, output_file)
