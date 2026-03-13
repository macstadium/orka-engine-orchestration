#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
# ]
# ///
"""
Update OCI registry credentials in Semaphore.

Useful for rotating credentials (e.g. short-lived ECR tokens) without
re-running the full configure_semaphore.py setup.

Usage:
    uv run semaphore/update_oci_credentials.py [options]

Options:
    --oci-username      OCI registry username
                        (default: $OCI_USERNAME)
    --oci-password      OCI registry password
                        (default: $OCI_PASSWORD)
    --environment-name  Semaphore environment to update (default: "OCI Credentials")
    --semaphore-url     Semaphore base URL (default: http://localhost:3000)
    --semaphore-admin   Admin username (default: $SEMAPHORE_ADMIN or "admin")
    --semaphore-password Admin password (default: $SEMAPHORE_ADMIN_PASSWORD or "changeme")
    --project-name      Project to update (default: "Orka Engine Orchestration")
"""

import argparse
import json
import os
import sys

import requests


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def upsert_oci_credentials(
    session: requests.Session,
    base: str,
    project_id: int,
    oci_username: str,
    oci_password: str,
    environment_name: str = "OCI Credentials",
) -> None:
    """Upsert the OCI credentials in a Semaphore environment.

    Creates the environment if it doesn't exist, otherwise updates it.
    Only sets keys that are provided (non-empty).
    """
    resp = session.get(f"{base}/api/project/{project_id}/environment")
    resp.raise_for_status()
    envs = [e for e in resp.json() if e["name"] == environment_name]

    updates = {}
    if oci_username:
        updates["oci_username"] = oci_username
    if oci_password:
        updates["oci_password"] = oci_password

    if not updates:
        print(f"No OCI credentials provided; skipping environment '{environment_name}'")
        return

    if envs:
        env = envs[0]
        current = json.loads(env.get("json") or "{}")
        current.update(updates)
        env_payload = {
            "id": env["id"],
            "name": env["name"],
            "project_id": project_id,
            "json": json.dumps(current),
            "env": env.get("env"),
            "password": env.get("password"),
        }
        resp = session.put(
            f"{base}/api/project/{project_id}/environment/{env['id']}",
            json=env_payload,
        )
        if resp.status_code != 204:
            die(
                f"Failed to update OCI credentials environment "
                f"({resp.status_code}): {resp.text}"
            )
        print(f"Updated environment '{environment_name}' with OCI credentials")
    else:
        env_payload = {
            "name": environment_name,
            "project_id": project_id,
            "json": json.dumps(updates),
            "env": None,
            "password": None,
        }
        resp = session.post(
            f"{base}/api/project/{project_id}/environment", json=env_payload
        )
        if resp.status_code != 201:
            die(
                f"Failed to create OCI credentials environment "
                f"({resp.status_code}): {resp.text}"
            )
        print(f"Created environment '{environment_name}' with OCI credentials")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--oci-username",
        default=os.environ.get("OCI_USERNAME", ""),
        help="OCI registry username (default: $OCI_USERNAME)",
    )
    parser.add_argument(
        "--oci-password",
        default=os.environ.get("OCI_PASSWORD", ""),
        help="OCI registry password (default: $OCI_PASSWORD)",
    )
    parser.add_argument(
        "--environment-name",
        default="OCI Credentials",
        help="Semaphore environment name to update",
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
    args = parser.parse_args()

    if not args.oci_username and not args.oci_password:
        die(
            "No OCI credentials provided. "
            "Pass --oci-username/--oci-password or set OCI_USERNAME/OCI_PASSWORD."
        )

    base = args.semaphore_url.rstrip("/")
    session = requests.Session()

    resp = session.post(
        f"{base}/api/auth/login",
        json={"auth": args.semaphore_admin, "password": args.semaphore_password},
    )
    if resp.status_code != 204:
        die(f"Login failed ({resp.status_code}): {resp.text}")
    print("Logged in to Semaphore")

    resp = session.get(f"{base}/api/projects")
    resp.raise_for_status()
    projects = [p for p in resp.json() if p["name"] == args.project_name]
    if not projects:
        die(f"Project '{args.project_name}' not found")
    project_id = projects[0]["id"]
    print(f"Found project '{args.project_name}' (ID: {project_id})")

    upsert_oci_credentials(
        session=session,
        base=base,
        project_id=project_id,
        oci_username=args.oci_username,
        oci_password=args.oci_password,
        environment_name=args.environment_name,
    )

    session.post(f"{base}/api/auth/logout")

    print("\nDone.")


if __name__ == "__main__":
    main()