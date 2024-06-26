import csv

def read_ids_from_csv(file_path):
    ids = set()
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ids.add(row['id'])
    return ids

def find_skipped_ids(file1_path, file2_path):
    ids_file1 = read_ids_from_csv(file1_path)
    ids_file2 = read_ids_from_csv(file2_path)

    skipped_ids = ids_file1 - ids_file2
    return skipped_ids

def output_skipped_ids(file1_path, file2_path):
    skipped_ids = find_skipped_ids(file1_path, file2_path)

    if not skipped_ids:
        print("No IDs from file 1 were skipped in file 2. All IDs are present.")
    else:
        print(f"IDs from file 1 that were skipped in file 2:")
        for id in sorted(skipped_ids):
            print(id)
        print(f"\nTotal IDs skipped: {len(skipped_ids)}")

file1_path = 'C:/Users/X/Desktop/Malicious-Commits/commits_with_repo_url.csv'
file2_path = 'C:/Users/X/Desktop/Malicious-Commits/commits_with_parent_ids.csv'
output_skipped_ids(file1_path, file2_path)