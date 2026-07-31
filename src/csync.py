import json
import os
from pathlib import Path
from rclone_python import rclone

def get_installed_remotes() -> set:
    """
    Fetches the set of active Rclone remotes configured on the system.
    """
    try:
        # Strip trailing colons returned by rclone (e.g., 'gdrive:' -> 'gdrive')
        return {r.replace(":", "") for r in rclone.get_remotes()}
    except Exception as e:
        print(f"Warning: Could not fetch rclone remotes list: {e}")
        return set()

def mirror_cloud_folder(remote_name: str, remote_folder: str, local_path: str, delete_extra: bool = False):
    """
    Mirrors a consumer cloud folder to a local directory.
    """
    local_dir = Path(local_path)
    local_dir.mkdir(parents=True, exist_ok=True)

    remote_full_spec = f"{remote_name}:{remote_folder.strip('/')}"

    if delete_extra:
        # Full mirror: deletes extra local files not present in the cloud
        print(f"Syncing [{remote_full_spec}] -> [{local_dir.resolve()}]...")
        rclone.sync(remote_full_spec, str(local_dir), show_progress=False)
        print("Sync complete.")
    else:
        # Safe mirror: only adds missing or updated files
        print(f"Copying [{remote_full_spec}] -> [{local_dir.resolve()}]...")
        rclone.copy(remote_full_spec, str(local_dir), show_progress=False)
        print("Copying complete.")

def run_cloud_sync(config_file_path: str):
    if not os.path.exists(config_file_path):
        print(f"Error: Config file '{config_file_path}' not found.")
        return

    with open(config_file_path, "r") as f:
        config = json.load(f)

    cloud = config.get("cloud", None)
    if not cloud: return
    enabled = cloud.get("enabled", False)
    if not enabled: return

    # Retrieve all authorized Rclone remotes once upfront
    active_remotes = get_installed_remotes()

    jobs = cloud.get("sync_jobs", [])
    for job in jobs:
        enabled = job.get("enabled", False)
        if not enabled: continue

        job_name = job.get("name", "Unnamed Job")
        remote_name = job.get("provider_remote")

        print(f"Cloud check: '{job_name}'...")

        # Check if the requested provider is authorized locally
        if remote_name not in active_remotes:
            print(
                f"Remote '{remote_name}' is not configured/authorized on this machine.\n"
                f"Run 'rclone config' in your terminal to set up '{remote_name}'."
            )
            continue

        # Execute verified job
        try:
            mirror_cloud_folder(
                remote_name=remote_name,
                remote_folder=job["remote_folder"],
                local_path=job["local_path"],
                delete_extra=job.get("delete_extra_local_files", False)
            )
        except Exception as e:
            print(f"Error running job '{job_name}': {e}")


if __name__ == "__main__":
    run_cloud_sync("config.json")