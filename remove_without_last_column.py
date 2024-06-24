import csv


def remove_rows_with_empty_last_column(input_file, output_file):
    rows_processed = 0
    rows_removed = 0

    with open(input_file, "r", newline="") as infile, open(
        output_file, "w", newline=""
    ) as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # Write the header
        header = next(reader)
        writer.writerow(header)

        for row in reader:
            rows_processed += 1
            if row[-1].strip():  # Check if the last column is not empty
                writer.writerow(row)
            else:
                rows_removed += 1

    return rows_processed, rows_removed


# Usage
input_file = "commits_with_parent_ids.csv"
output_file = "final_output.csv"

rows_processed, rows_removed = remove_rows_with_empty_last_column(
    input_file, output_file
)

print(f"Total rows processed: {rows_processed}")
print(f"Rows removed (empty last column): {rows_removed}")
print(f"Rows in final output: {rows_processed - rows_removed}")
