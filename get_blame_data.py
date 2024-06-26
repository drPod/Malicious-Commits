import csv
import os
import subprocess
from git import Repo
import git
from tqdm import tqdm
import logging
import traceback
import requests

log_filename = "blame_processing.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

PATCH_CACHE_DIR = "patch_cache"


def ensure_cache_dir():
    """Ensure the patch cache directory exists."""
    os.makedirs(PATCH_CACHE_DIR, exist_ok=True)


def get_cached_patch_path(commit_url):
    """Generate a unique filename for caching the patch."""
    # Use the last part of the URL as the filename, replacing '/' with '_'
    filename = commit_url.split("/")[-1].replace("/", "_") + ".patch"
    return os.path.join(PATCH_CACHE_DIR, filename)


def get_patch_info(commit_url):
    try:
        clean_url = commit_url.split("#")[0]
        patch_url = clean_url + ".patch"
        cached_patch_path = get_cached_patch_path(clean_url)

        if os.path.exists(cached_patch_path):
            logging.info(f"Using cached patch for: {clean_url}")
            with open(cached_patch_path, "r") as patch_file:
                patch_content = patch_file.read()
        else:
            logging.info(f"Fetching patch from: {patch_url}")
            wget_command = ["wget", "-q", "-O", cached_patch_path, patch_url]
            subprocess.run(wget_command, check=True)

            with open(cached_patch_path, "r") as patch_file:
                patch_content = patch_file.read()

        file_changes = {}
        current_file = None
        in_changelog = False

        for line_number, line in enumerate(patch_content.split("\n"), 1):
            try:
                if line.startswith("---"):
                    parts = line.split(" ")
                    if len(parts) > 1:
                        current_file = parts[1][2:]
                        logging.debug(f"New file detected: {current_file}")
                        file_changes[current_file] = []
                        in_changelog = False
                    else:
                        logging.debug(
                            f"Changelog section started at line {line_number} - ignoring"
                        )
                        in_changelog = True
                elif not in_changelog:
                    if line.startswith("-") and not line.startswith("---"):
                        if current_file is not None:
                            file_changes[current_file].append(line[1:])
                            # logging.debug(f"Added removed line to {current_file}: {line[1:]}")
                        else:
                            logging.warning(
                                f"Removed line found before file declaration at line {line_number}: {line}"
                            )
            except Exception as e:
                logging.error(f"Error processing line {line_number}: {line}")
                logging.error(f"Error details: {str(e)}")

        logging.info(
            f"Patch processing complete. Files changed: {list(file_changes.keys())}"
        )
        for file, changes in file_changes.items():
            logging.info(f"File {file} has {len(changes)} removed lines")

        return file_changes
    except subprocess.CalledProcessError as e:
        logging.warning(f"Failed to fetch patch. wget error: {e}")
        return None
    except Exception as e:
        logging.error(f"Error in get_patch_info for {commit_url}: {str(e)}")
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return None

def check_repo_exists(repo_url):
    try:
        response = requests.head(repo_url)
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Error checking repository {repo_url}: {str(e)}")
        return False

def clone_repo_if_not_exists(repo_url, repo_path):
    if not check_repo_exists(repo_url):
        return False
    try:
        if not os.path.exists(repo_path):
            logging.info(f"Attempting to clone repository: {repo_url}")
        if not os.path.exists(repo_path):
            logging.info(f"Cloning repository: {repo_url}")
            Repo.clone_from(repo_url, repo_path)
            logging.info(f"Repository clone finished: {repo_url}")
    except Exception as e:
        logging.error(f"Error in clone_repo_if_not_exists for {repo_url}: {str(e)}")
        raise


def get_processed_commits(output_file):
    processed_commits = set()
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_commits.add(row["commit_id"])
    return processed_commits


def process_commits(input_file, output_file):
    processed_commits = get_processed_commits(output_file)

    with open(input_file, "r") as in_f, open(output_file, "a", newline="") as out_f:
        reader = csv.DictReader(in_f)
        fieldnames = reader.fieldnames + ["malicious_files", "malicious_commit_hashes"]

        writer = csv.DictWriter(out_f, fieldnames=fieldnames)

        if out_f.tell() == 0:
            writer.writeheader()

        # Count total commits
        total_commits = sum(1 for _ in reader)
        in_f.seek(0)  # Reset file pointer
        reader = csv.DictReader(in_f)  # Recreate reader

        # Create progress bar
        pbar = tqdm(reader, desc="Processing commits", total=total_commits, 
                    unit="commit", ncols=100, 
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")

        for row in pbar:
            commit_id = row["commit_id"]
            parent_commit_id = row["parent_commit_id"]
            commit_url = row["commit_url"]
            repo_url = row["repo_url"]

            pbar.set_postfix({"Current Commit": commit_id[:7]})

            if commit_id in processed_commits:
                logging.info(f"Skipping already processed commit: {commit_id}")
                continue

            try:
                repo_cache = "repo_cache"
                os.makedirs(repo_cache, exist_ok=True)
                repo_name = repo_url.split("/")[-1]
                repo_path = os.path.join(repo_cache, repo_name)

                if not clone_repo_if_not_exists(repo_url, repo_path):
                    logging.warning(f"Skipping repository: {repo_url}")
                    continue

                repo = Repo(repo_path)
                logging.info(f"Resetting to parent commit: {parent_commit_id}")
                try:
                    repo.git.reset("--hard", parent_commit_id)
                except git.exc.GitCommandError:
                    logging.warning(f"Could not reset to parent commit: {parent_commit_id}. Skipping.")
                    continue

                patch_info = get_patch_info(commit_url)
                if not patch_info:
                    logging.warning(f"No patch info found for commit: {commit_id}")
                    continue

                malicious_commit_hashes = set()
                malicious_files = set()

                for filename, removed_lines in patch_info.items():
                    if not removed_lines:
                        continue

                    try:
                        blame_output = repo.git.blame("-l", commit_id, "--", filename)
                    except git.exc.GitCommandError:
                        logging.warning(f"Could not run git blame on file: {filename}. Skipping file.")
                        continue

                    file_is_malicious = False
                    for line in blame_output.split("\n"):
                        hash_and_line = line.split(")")[0]
                        commit_hash = hash_and_line.split(" ")[0]
                        line_content = line.split(")")[1].strip()
                        if line_content in removed_lines:
                            malicious_commit_hashes.add(commit_hash)
                            file_is_malicious = True

                    if file_is_malicious:
                        malicious_files.add(filename)

                row["malicious_files"] = ",".join(malicious_files)
                row["malicious_commit_hashes"] = ",".join(malicious_commit_hashes)

                writer.writerow(row)
                out_f.flush()  # Ensure the write is committed to disk

                processed_commits.add(commit_id)
                pbar.set_postfix({"Current Commit": commit_id[:7], 
                                  "Malicious Files": len(malicious_files), 
                                  "Malicious Hashes": len(malicious_commit_hashes)})
                logging.info(
                    f"Processed commit: {commit_id}. Found {len(malicious_files)} malicious files and {len(malicious_commit_hashes)} malicious commit hashes."
                )
            except Exception as e:
                logging.error(f"Error processing commit {commit_id}: {str(e)}")
                logging.error(f"Full traceback: {traceback.format_exc()}")

    logging.info(f"Processing complete. Results saved to {output_file}")


if __name__ == "__main__":
    input_file = "commits_with_parent_ids.csv"
    output_file = "commits_with_blame_data.csv"
    process_commits(input_file, output_file)
    print(f"Processing complete. Results saved to {output_file}")
    print(f"Log file: {log_filename}")
    print(f"Patch cache directory: {PATCH_CACHE_DIR}")
