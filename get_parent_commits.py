import csv
import os
import subprocess
import shutil
from git import Repo


def clone_repo_and_get_parent(repo_url, commit_id):
    repo_name = repo_url.split("/")[-1]
    try:
        # Clone the repository
        repo = Repo.clone_from(repo_url, repo_name)

        # Checkout the specific commit
        repo.git.checkout(commit_id)

        # Get the parent commit ID
        parent_commit = repo.commit(commit_id).parents[0].hexsha

        # Clean up: remove the cloned repository
        shutil.rmtree(repo_name)

        return parent_commit
    except Exception as e:
        print(f"Error processing {repo_url}: {str(e)}")
        return None


def process_commits(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w", newline="") as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["parent_commit_id"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            repo_url = row["repo_url"]
            commit_id = row["commit_id"]

            parent_commit_id = clone_repo_and_get_parent(repo_url, commit_id)
            row["parent_commit_id"] = parent_commit_id

            writer.writerow(row)


if __name__ == "__main__":
    input_file = "commits_with_repo_url.csv"
    output_file = "commits_with_parent_ids.csv"
    process_commits(input_file, output_file)
