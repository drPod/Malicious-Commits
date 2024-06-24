import csv
import os
import shutil
from git import Repo, GitCommandError
import time
import logging
from tqdm import tqdm

logging.basicConfig(
    filename="repo_processing.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def clean_lock_files(repo_path):
    lock_files = [
        os.path.join(repo_path, ".git", "index.lock"),
        os.path.join(repo_path, ".git", "shallow.lock"),
    ]
    for lock_file in lock_files:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception as e:
                logging.error(f"Failed to remove lock file {lock_file}: {str(e)}")


def clone_repo_and_get_parent(repo_url, commit_id, repo_cache):
    repo_name = repo_url.split("/")[-1]
    repo_path = os.path.join(repo_cache, repo_name)

    # Set environment variables to prevent Git from prompting for credentials
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    os.environ["GIT_ASKPASS"] = "echo"
    os.environ["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"

    for attempt in range(3):  # Try up to 3 times
        try:
            clean_lock_files(repo_path)

            if not os.path.exists(repo_path):
                logging.info(f"Cloning repository: {repo_url}")
                repo = Repo.clone_from(repo_url, repo_path, depth=1000)
            else:
                logging.info(f"Repository exists, fetching: {repo_url}")
                repo = Repo(repo_path)
                repo.remote().fetch(depth=1000)

            logging.info(f"Checking out commit: {commit_id}")
            repo.git.checkout(commit_id)

            parent_commit = repo.commit(commit_id).parents[0].hexsha
            logging.info(f"Found parent commit: {parent_commit}")

            return parent_commit
        except GitCommandError as e:
            error_message = str(e)
            logging.error(
                f"GitCommandError processing {repo_url} (attempt {attempt+1}): {error_message}"
            )
            if (
                "unable to read tree" in error_message
                or "does not exist" in error_message
            ):
                logging.info(f"Attempting full clone for {repo_url}")
                shutil.rmtree(repo_path, ignore_errors=True)
                repo = Repo.clone_from(repo_url, repo_path)
            elif (
                "Authentication failed" in error_message
                or "could not read Username" in error_message
            ):
                logging.warning(
                    f"Repository {repo_url} requires authentication. Skipping."
                )
                return None
            elif attempt == 2:  # Last attempt
                return None
        except Exception as e:
            logging.error(
                f"Error processing {repo_url} (attempt {attempt+1}): {str(e)}"
            )
            if attempt == 2:  # Last attempt
                return None
        time.sleep(5 * (attempt + 1))  # Increasing delay between retries


def process_commits(input_file, output_file):
    repo_cache = "repo_cache"
    os.makedirs(repo_cache, exist_ok=True)

    # Read existing output to determine where to resume
    processed_commits = set()
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_commits.add(row["commit_id"])

    with open(input_file, "r") as infile, open(output_file, "a", newline="") as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(
            outfile, fieldnames=reader.fieldnames + ["parent_commit_id"]
        )

        # Write header if the file is empty
        if outfile.tell() == 0:
            writer.writeheader()

        total_rows = sum(1 for row in reader) - len(processed_commits)
        infile.seek(0)
        reader = csv.DictReader(infile)

        with tqdm(total=total_rows, desc="Processing commits") as pbar:
            for row in reader:
                if row["commit_id"] in processed_commits:
                    continue  # Skip already processed commits

                parent_commit = clone_repo_and_get_parent(
                    row["repo_url"], row["commit_id"], repo_cache
                )
                row["parent_commit_id"] = parent_commit
                writer.writerow(row)
                outfile.flush()  # Ensure data is written immediately
                pbar.update(1)

    logging.info("Cleaning up repo cache")
    shutil.rmtree(repo_cache, ignore_errors=True)


if __name__ == "__main__":
    input_file = "commits_with_repo_url.csv"
    output_file = "commits_with_parent_ids.csv"
    start_time = time.time()
    process_commits(input_file, output_file)
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time} seconds")
    print(f"Check 'repo_processing.log' for detailed processing information.")
