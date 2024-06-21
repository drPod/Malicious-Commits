import csv
from urllib.parse import urlparse


def extract_repo_url(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w", newline="") as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["repo_url"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            commit_url = row["commit_url"]
            parsed_url = urlparse(commit_url)
            repo_url = f"{parsed_url.scheme}://{parsed_url.netloc}/{'/'.join(parsed_url.path.split('/')[:3])}"
            row["repo_url"] = repo_url
            writer.writerow(row)


# Example usage
input_file = "commits.csv"
output_file = "commits_with_repo_url.csv"
extract_repo_url(input_file, output_file)
