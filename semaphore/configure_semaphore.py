#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
# ]
# ///
"""
Configure Semaphore via API: add an SSH key and update project resources to use it.

Usage:
    uv run semaphore/configure_semaphore.py --ssh-key-file /path/to/id_rsa

Options:
    --ssh-key-file      (required) Path to the SSH private key file to upload
    --ssh-key-name      Name for the key in Semaphore (default: "SSH Key")
    --semaphore-url     Semaphore base URL (default: http://localhost:3000)
    --semaphore-admin   Admin username (default: $SEMAPHORE_ADMIN or "admin")
    --semaphore-password Admin password (default: $SEMAPHORE_ADMIN_PASSWORD or "changeme")
    --project-name      Project to update (default: "Orka Engine Orchestration")
    --repository-name   Repository to update (default: "Local Playbooks")
    --inventory-name    Inventory to update (default: "Dev Inventory")
"""

import argparse
import os
import sys

import requests


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--ssh-key-file", required=True, help="Path to SSH private key file"
    )
    parser.add_argument(
        "--ssh-key-name", default="SSH Key", help="Name for the key in Semaphore"
    )
    parser.add_argument(
        "--semaphore-url", default="http://localhost:3000", help="Semaphore base URL"
    )
    parser.add_argument(
        "--semaphore-admin", default=os.environ.get("SEMAPHORE_ADMIN", "admin")
    )
    parser.add_argument(
        "--semaphore-password",
        default=os.environ.get("SEMAPHORE_ADMIN_PASSWORD", "changeme"),
    )
    parser.add_argument("--project-name", default="Orka Engine Orchestration")
    parser.add_argument("--repository-name", default="Local Playbooks")
    parser.add_argument("--inventory-name", default="Dev Inventory")
    args = parser.parse_args()

    base = args.semaphore_url.rstrip("/")

    # Read SSH key
    try:
        with open(args.ssh_key_file) as f:
            private_key = f.read()
    except OSError as e:
        die(f"Cannot read SSH key file: {e}")

    session = requests.Session()

    # Login
    resp = session.post(
        f"{base}/api/auth/login",
        json={"auth": args.semaphore_admin, "password": args.semaphore_password},
    )
    if resp.status_code != 204:
        die(f"Login failed ({resp.status_code}): {resp.text}")
    print("Logged in to Semaphore")

    # Find project
    resp = session.get(f"{base}/api/projects")
    resp.raise_for_status()
    projects = [p for p in resp.json() if p["name"] == args.project_name]
    if not projects:
        die(f"Project '{args.project_name}' not found")
    project_id = projects[0]["id"]
    print(f"Found project '{args.project_name}' (ID: {project_id})")

    # Upsert SSH key
    resp = session.get(f"{base}/api/project/{project_id}/keys")
    resp.raise_for_status()
    existing = [k for k in resp.json() if k["name"] == args.ssh_key_name]

    key_payload = {
        "name": args.ssh_key_name,
        "type": "ssh",
        "project_id": project_id,
        "override_secret": True,
        "ssh": {"login": "", "passphrase": "", "private_key": private_key},
    }

    if existing:
        key_id = existing[0]["id"]
        key_payload["id"] = key_id
        resp = session.put(
            f"{base}/api/project/{project_id}/keys/{key_id}", json=key_payload
        )
        if resp.status_code != 204:
            die(f"Failed to update SSH key ({resp.status_code}): {resp.text}")
        print(f"Updated SSH key '{args.ssh_key_name}' (ID: {key_id})")
    else:
        resp = session.post(f"{base}/api/project/{project_id}/keys", json=key_payload)
        if resp.status_code != 201:
            die(f"Failed to create SSH key ({resp.status_code}): {resp.text}")
        key_id = resp.json()["id"]
        print(f"Created SSH key '{args.ssh_key_name}' (ID: {key_id})")

    # Update repository
    resp = session.get(f"{base}/api/project/{project_id}/repositories")
    resp.raise_for_status()
    repos = [r for r in resp.json() if r["name"] == args.repository_name]
    if not repos:
        die(
            f"Repository '{args.repository_name}' not found in project '{args.project_name}'"
        )
    repo = repos[0]
    repo_payload = {
        "id": repo["id"],
        "name": repo["name"],
        "project_id": project_id,
        "git_url": repo["git_url"],
        "git_branch": repo.get("git_branch", ""),
        "ssh_key_id": key_id,
    }
    resp = session.put(
        f"{base}/api/project/{project_id}/repositories/{repo['id']}", json=repo_payload
    )
    if resp.status_code != 204:
        die(f"Failed to update repository ({resp.status_code}): {resp.text}")
    print(f"Updated repository '{args.repository_name}' to use SSH key")

    # Update inventory
    resp = session.get(f"{base}/api/project/{project_id}/inventory")
    resp.raise_for_status()
    inventories = [i for i in resp.json() if i["name"] == args.inventory_name]
    if not inventories:
        die(
            f"Inventory '{args.inventory_name}' not found in project '{args.project_name}'"
        )
    inv = inventories[0]
    inv_payload = {
        "id": inv["id"],
        "name": inv["name"],
        "project_id": project_id,
        "inventory": inv["inventory"],
        "ssh_key_id": key_id,
        "become_key_id": None,
        "type": inv["type"],
    }
    resp = session.put(
        f"{base}/api/project/{project_id}/inventory/{inv['id']}", json=inv_payload
    )
    if resp.status_code != 204:
        die(f"Failed to update inventory ({resp.status_code}): {resp.text}")
    print(
        f"Updated inventory '{args.inventory_name}' to use SSH key, become key cleared"
    )

    # Logout
    session.post(f"{base}/api/auth/logout")

    print("\nSummary:")
    print(f"  SSH key '{args.ssh_key_name}' (ID: {key_id}) added/updated")
    print(f"  Repository '{args.repository_name}' updated to use SSH key")
    print(
        f"  Inventory '{args.inventory_name}' updated to use SSH key, become key cleared"
    )


if __name__ == "__main__":
    main()
