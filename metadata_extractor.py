import csv
import os
import json
from git import Repo
import logging
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    filename="commit_metadata.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def get_commit_metadata(repo, commit_hash):
    try:
        commit = repo.commit(commit_hash)
        return {
            "hash": commit.hexsha,
            "author": commit.author.name,
            "author_email": commit.author.email,
            "committed_date": commit.committed_datetime.isoformat(),
            "message": commit.message.strip(),
            "files_changed": list(commit.stats.files.keys()),
            "insertions": commit.stats.total["insertions"],
            "deletions": commit.stats.total["deletions"],
        }
    except Exception as e:
        logging.error(f"Error retrieving metadata for commit {commit_hash}: {str(e)}")
        return None


def load_existing_data(output_file):
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            return json.load(f)
    return {}


def get_or_create_repo(repo_url, repo_cache_dir):
    repo_name = repo_url.split("/")[-1]
    repo_path = os.path.join(repo_cache_dir, repo_name)
    if not os.path.exists(repo_path):
        logging.info(f"Cloning repository: {repo_url}")
        try:
            repo = Repo.clone_from(repo_url, repo_path)
            logging.info(f"Successfully cloned repository: {repo_url}")
            return repo
        except Exception as e:
            logging.error(f"Error cloning repository {repo_url}: {str(e)}")
            return None
    else:
        try:
            repo = Repo(repo_path)
            repo.remotes.origin.pull()
            logging.info(f"Successfully updated repository: {repo_url}")
            return repo
        except Exception as e:
            logging.error(
                f"Error opening or updating repository at {repo_path}: {str(e)}"
            )
            return None


def process_commits(input_file, output_file, repo_cache_dir):
    os.makedirs(repo_cache_dir, exist_ok=True)

    commit_data = load_existing_data(output_file)
    repos = {}

    with open(input_file, "r") as in_f:
        reader = csv.DictReader(in_f)
        total_rows = sum(1 for row in reader)
        in_f.seek(0)
        next(reader)  # Skip header row

        for row in tqdm(reader, desc="Processing commits", total=total_rows):
            cve_id = row["cve_id"]
            project_name = row["project_name"]
            repo_url = row["repo_url"]
            malicious_hashes = row["malicious_commit_hashes"].split(",")
            malicious_files = row["malicious_files"].split(",")

            if cve_id not in commit_data:
                commit_data[cve_id] = {}

            if project_name not in commit_data[cve_id]:
                commit_data[cve_id][project_name] = []

            if repo_url not in repos:
                repo = get_or_create_repo(repo_url, repo_cache_dir)
                if repo is None:
                    continue
                repos[repo_url] = repo
            else:
                repo = repos[repo_url]

            for hash in malicious_hashes:
                if any(
                    commit["original_hash"] == hash.strip()
                    for commit in commit_data[cve_id][project_name]
                ):
                    logging.info(f"Skipping already processed commit: {hash.strip()}")
                    continue

                metadata = get_commit_metadata(repo, hash.strip())
                if metadata:
                    metadata["original_hash"] = hash.strip()
                    metadata["malicious_files"] = malicious_files
                    commit_data[cve_id][project_name].append(metadata)

            with open(output_file, "w") as out_f:
                json.dump(commit_data, out_f, indent=2)

    logging.info(f"Processing complete. Results saved to {output_file}")


if __name__ == "__main__":
    input_file = "commits_with_blame_data.csv"
    output_file = (
        "commit_metadata.json"  # Changed: Now directly in the script directory
    )
    repo_cache_dir = os.path.join("repo_cache")
    process_commits(input_file, output_file, repo_cache_dir)
    print(f"Processing complete. Results saved to {output_file}")
    print(f"Log file: commit_metadata.log")
