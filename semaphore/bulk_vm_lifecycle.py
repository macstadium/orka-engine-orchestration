#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "python-dotenv",
#   "requests",
# ]
# ///
"""
Bulk VM lifecycle management via the Semaphore UI REST API.

Provision, list, manage, delete, and provision users on groups of VMs
identified by a shared name prefix. Each deployed VM gets a name of the
form ``<prefix>-<random>`` (e.g. ``demo-a1b2c3d4``), and the script writes
a manifest at ``semaphore/.bulk_vms_<prefix>.json`` so that subsequent
commands can target the exact set of VMs that were provisioned.

Subcommands:
    deploy          Create N VMs with the given prefix.
    list            List VMs whose names start with the prefix.
    manage          Set all VMs with the prefix to a desired state
                    (running/stopped/absent).
    delete          Shortcut for ``manage --state absent``; also removes
                    the local manifest.
    provision-user  Provision a user on every VM in the manifest
                    (or on an explicit list passed via --vm-names).
    install-citrix  Install the Citrix VDA on every VM in the manifest
                    (or on an explicit list passed via --vm-names).

Examples:
    uv run semaphore/bulk_vm_lifecycle.py deploy \\
        --prefix demo --count 5 \\
        --vm-image oci://ghcr.io/example/base:latest

    uv run semaphore/bulk_vm_lifecycle.py list --prefix demo
    uv run semaphore/bulk_vm_lifecycle.py manage --prefix demo --state stopped
    uv run semaphore/bulk_vm_lifecycle.py provision-user \\
        --prefix demo --username dev --password 's3cret'
    uv run semaphore/bulk_vm_lifecycle.py install-citrix --prefix demo
    uv run semaphore/bulk_vm_lifecycle.py delete --prefix demo --yes

Common options for every subcommand:
    --semaphore-url       Semaphore base URL (default: http://localhost:3000)
    --semaphore-admin     Admin username (default: $SEMAPHORE_ADMIN or "admin")
    --semaphore-password  Admin password (default: $SEMAPHORE_ADMIN_PASSWORD or "changeme")
    --project-name        Project containing the VM templates
                          (default: "Orka Engine Orchestration")
    --wait / --no-wait    Whether to poll until tasks reach a terminal state
                          (default: --wait)
    --poll-interval       Seconds between status polls (default: 3)
    --task-timeout        Per-task timeout in seconds (default: 1800)
    --concurrency         Max parallel task submissions (default: 5)

Defaults for credentials and URL may also come from ``semaphore/.env``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

TEMPLATES = {
    "deploy": "Virtual Machines | Deploy VM",
    "list": "Virtual Machines | List VMs",
    "manage": "Virtual Machines | Manage VM",
    "provision_user": "Virtual Machines | Provision User to VM",
    "install_citrix": "VDI | Install Citrix VDA",
}

TERMINAL_STATUSES = {"success", "error", "stopped"}
PREFIX_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}[a-z0-9]$")


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def validate_prefix(prefix: str) -> str:
    if not PREFIX_PATTERN.match(prefix):
        die(
            f"Invalid prefix '{prefix}': must be lowercase alphanumeric or hyphen, "
            "2-32 chars, and start/end with an alphanumeric"
        )
    return prefix


def manifest_path(prefix: str) -> Path:
    return SCRIPT_DIR / f".bulk_vms_{prefix}.json"


def read_manifest(prefix: str) -> dict[str, Any] | None:
    path = manifest_path(prefix)
    if not path.exists():
        return None
    with path.open(encoding="utf8") as f:
        return json.load(f)


def write_manifest(prefix: str, vm_names: list[str]) -> Path:
    path = manifest_path(prefix)
    data = {
        "prefix": prefix,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "vm_names": sorted(vm_names),
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")
    return path


def merge_manifest(prefix: str, new_names: list[str]) -> Path:
    existing = read_manifest(prefix)
    combined = set(new_names)
    if existing:
        combined.update(existing.get("vm_names", []))
    return write_manifest(prefix, sorted(combined))


def delete_manifest(prefix: str) -> bool:
    path = manifest_path(prefix)
    if path.exists():
        path.unlink()
        return True
    return False


def random_vm_name(prefix: str, length: int = 8) -> str:
    return f"{prefix}-{secrets.token_hex(length // 2)}"


def login(session: requests.Session, base: str, user: str, password: str) -> None:
    resp = session.post(
        f"{base}/api/auth/login",
        json={"auth": user, "password": password},
    )
    if resp.status_code != 204:
        die(f"Login failed ({resp.status_code}): {resp.text}")


def find_project_id(session: requests.Session, base: str, name: str) -> int:
    resp = session.get(f"{base}/api/projects")
    resp.raise_for_status()
    for project in resp.json():
        if project["name"] == name:
            return project["id"]
    die(f"Project '{name}' not found")


def find_template_id(
    session: requests.Session, base: str, project_id: int, name: str
) -> int:
    resp = session.get(f"{base}/api/project/{project_id}/templates")
    resp.raise_for_status()
    for template in resp.json():
        if template["name"] == name:
            return template["id"]
    die(f"Template '{name}' not found in project (id={project_id})")


def submit_task(
    session: requests.Session,
    base: str,
    project_id: int,
    template_id: int,
    survey_vars: dict[str, Any],
    message: str = "",
) -> int:
    """Submit a task and return its ID.

    Survey variables are passed via Semaphore's task ``environment`` field as a
    JSON-encoded object — the same wire format the UI uses. The task-level
    ``params`` field is reserved for ``AnsibleTaskParams`` (debug/tags/limit/etc.)
    and silently drops unknown keys, so survey vars sent there never reach the
    playbook.
    """
    body = {
        "template_id": template_id,
        "playbook": "",
        "environment": json.dumps(survey_vars),
        "limit": "",
        "git_branch": "",
        "message": message,
    }
    resp = session.post(f"{base}/api/project/{project_id}/tasks", json=body)
    if resp.status_code not in (200, 201):
        die(
            f"Failed to submit task for template {template_id} with vars "
            f"{survey_vars}: {resp.status_code} {resp.text}"
        )
    data = resp.json()
    task_id = data.get("id") or data.get("task_id")
    if not task_id:
        die(f"Task submission returned no id: {data}")
    return task_id


def get_task(
    session: requests.Session, base: str, project_id: int, task_id: int
) -> dict[str, Any]:
    resp = session.get(f"{base}/api/project/{project_id}/tasks/{task_id}")
    resp.raise_for_status()
    return resp.json()


def get_task_output(
    session: requests.Session, base: str, project_id: int, task_id: int
) -> str:
    resp = session.get(f"{base}/api/project/{project_id}/tasks/{task_id}/output")
    if resp.status_code != 200:
        return ""
    try:
        lines = resp.json()
    except ValueError:
        return resp.text
    if isinstance(lines, list):
        return "\n".join(line.get("output", "") for line in lines)
    return str(lines)


def wait_for_task(
    session: requests.Session,
    base: str,
    project_id: int,
    task_id: int,
    poll_interval: float,
    timeout: float,
    label: str,
) -> dict[str, Any]:
    """Poll a task until terminal or timeout. Returns the final task object."""
    deadline = time.monotonic() + timeout
    last_status: str | None = None
    while True:
        task = get_task(session, base, project_id, task_id)
        status = task.get("status", "")
        if status != last_status:
            print(f"  [{label}] task {task_id}: {status}")
            last_status = status
        if status in TERMINAL_STATUSES:
            return task
        if time.monotonic() >= deadline:
            print(
                f"  [{label}] task {task_id}: timed out after {timeout}s "
                f"(last status: {status})"
            )
            return task
        time.sleep(poll_interval)


FAILURE_OUTPUT_TAIL_LINES = 40


def task_ui_url(base: str, project_id: int, task_id: int) -> str:
    return f"{base}/project/{project_id}/templates?t={task_id}"


def print_failure_output(
    session: requests.Session,
    base: str,
    project_id: int,
    task_id: int,
    label: str,
) -> None:
    """Print the tail of a failed task's Ansible output plus its UI URL."""
    output = get_task_output(session, base, project_id, task_id)
    lines = [line for line in output.splitlines() if line.strip()]
    tail = lines[-FAILURE_OUTPUT_TAIL_LINES:]
    print(f"  [{label}] last {len(tail)} output line(s):")
    if tail:
        for line in tail:
            print(f"    | {line}")
    else:
        print("    | (no output captured)")
    print(f"  [{label}] full log: {task_ui_url(base, project_id, task_id)}")


def submit_and_wait(
    session: requests.Session,
    base: str,
    project_id: int,
    template_id: int,
    params: dict[str, Any],
    label: str,
    wait: bool,
    poll_interval: float,
    timeout: float,
    message: str,
) -> dict[str, Any]:
    task_id = submit_task(session, base, project_id, template_id, params, message)
    print(f"  [{label}] submitted task {task_id}")
    if not wait:
        return {"id": task_id, "status": "submitted", "label": label}
    task = wait_for_task(
        session, base, project_id, task_id, poll_interval, timeout, label
    )
    task["label"] = label
    if task.get("status") not in {"success", "submitted"}:
        print_failure_output(session, base, project_id, task_id, label)
    return task


def run_parallel(
    jobs: list[tuple[str, dict[str, Any]]],
    session: requests.Session,
    base: str,
    project_id: int,
    template_id: int,
    concurrency: int,
    wait: bool,
    poll_interval: float,
    timeout: float,
    message: str,
) -> list[dict[str, Any]]:
    """Submit and (optionally) wait for a set of tasks against one template."""
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = {
            pool.submit(
                submit_and_wait,
                session,
                base,
                project_id,
                template_id,
                params,
                label,
                wait,
                poll_interval,
                timeout,
                message,
            ): label
            for label, params in jobs
        }
        for future in as_completed(futures):
            results.append(future.result())
    return results


def summarize(results: list[dict[str, Any]]) -> int:
    """Print a summary; return number of failures."""
    succeeded = [r for r in results if r.get("status") == "success"]
    submitted = [r for r in results if r.get("status") == "submitted"]
    failed = [r for r in results if r.get("status") in {"error", "stopped"}]
    other = [
        r
        for r in results
        if r.get("status") not in {"success", "error", "stopped", "submitted"}
    ]

    print("\nSummary:")
    print(f"  total:     {len(results)}")
    if submitted:
        print(f"  submitted: {len(submitted)} (not waited on)")
    if succeeded:
        print(f"  success:   {len(succeeded)}")
    if failed:
        print(f"  failed:    {len(failed)}")
        for r in failed:
            print(f"    - {r.get('label')}: task {r.get('id')} -> {r.get('status')}")
    if other:
        print(f"  unknown:   {len(other)}")
        for r in other:
            print(f"    - {r.get('label')}: task {r.get('id')} -> {r.get('status')}")
    return len(failed) + len(other)


def cmd_deploy(args: argparse.Namespace, ctx: dict[str, Any]) -> int:
    prefix = validate_prefix(args.prefix)
    if args.count < 1:
        die("--count must be >= 1")

    existing = read_manifest(prefix)
    known: set[str] = set(existing["vm_names"]) if existing else set()
    new_names: list[str] = []
    while len(new_names) < args.count:
        candidate = random_vm_name(prefix, args.random_length)
        if candidate in known or candidate in new_names:
            continue
        new_names.append(candidate)

    print(f"Generating {len(new_names)} VM(s) with prefix '{prefix}':")
    for name in new_names:
        print(f"  - {name}")

    template_id = find_template_id(
        ctx["session"], ctx["base"], ctx["project_id"], TEMPLATES["deploy"]
    )

    base_params: dict[str, Any] = {
        "vm_image": args.vm_image,
        "public_image": "true" if args.public_image else "false",
        "cpu": str(args.cpu),
        "memory": str(args.memory),
    }
    if args.network_interface:
        base_params["network_interface"] = args.network_interface

    jobs = [(name, {**base_params, "vm_name": name}) for name in new_names]

    results = run_parallel(
        jobs,
        ctx["session"],
        ctx["base"],
        ctx["project_id"],
        template_id,
        args.concurrency,
        args.wait,
        args.poll_interval,
        args.task_timeout,
        message=f"Bulk deploy: prefix={prefix}",
    )

    if args.wait:
        successful = [r["label"] for r in results if r.get("status") == "success"]
    else:
        successful = [r["label"] for r in results if r.get("status") == "submitted"]

    if successful:
        path = merge_manifest(prefix, successful)
        print(f"\nWrote manifest with {len(successful)} VM(s): {path}")
    return summarize(results)


def cmd_list(args: argparse.Namespace, ctx: dict[str, Any]) -> int:
    prefix = validate_prefix(args.prefix)
    template_id = find_template_id(
        ctx["session"], ctx["base"], ctx["project_id"], TEMPLATES["list"]
    )
    task = submit_and_wait(
        ctx["session"],
        ctx["base"],
        ctx["project_id"],
        template_id,
        {"vm_name": prefix},
        label=f"list {prefix}",
        wait=args.wait,
        poll_interval=args.poll_interval,
        timeout=args.task_timeout,
        message=f"Bulk list: prefix={prefix}",
    )
    if args.wait and args.show_output:
        output = get_task_output(
            ctx["session"], ctx["base"], ctx["project_id"], task["id"]
        )
        print("\n----- task output -----")
        print(output)
        print("----- end output -----")
    return summarize([task])


def cmd_manage(args: argparse.Namespace, ctx: dict[str, Any]) -> int:
    prefix = validate_prefix(args.prefix)
    template_id = find_template_id(
        ctx["session"], ctx["base"], ctx["project_id"], TEMPLATES["manage"]
    )
    task = submit_and_wait(
        ctx["session"],
        ctx["base"],
        ctx["project_id"],
        template_id,
        {"vm_name": prefix, "desired_state": args.state},
        label=f"manage {prefix} -> {args.state}",
        wait=args.wait,
        poll_interval=args.poll_interval,
        timeout=args.task_timeout,
        message=f"Bulk manage: prefix={prefix} state={args.state}",
    )
    return summarize([task])


def cmd_delete(args: argparse.Namespace, ctx: dict[str, Any]) -> int:
    prefix = validate_prefix(args.prefix)
    if not args.yes:
        manifest = read_manifest(prefix)
        known = manifest["vm_names"] if manifest else None
        if known:
            print(f"About to delete {len(known)} VM(s) with prefix '{prefix}':")
            for name in known:
                print(f"  - {name}")
        else:
            print(
                f"About to delete ALL VMs whose names start with '{prefix}' "
                "(no local manifest found; relying on server-side prefix match)."
            )
        confirm = input("Type 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            return 1

    args.state = "absent"
    failures = cmd_manage(args, ctx)
    if failures == 0:
        removed = delete_manifest(prefix)
        if removed:
            print(f"Removed manifest {manifest_path(prefix)}")
    else:
        print(
            f"Manifest preserved at {manifest_path(prefix)} due to "
            f"{failures} failed task(s)."
        )
    return failures


def resolve_vm_names(args: argparse.Namespace, prefix: str) -> list[str]:
    if args.vm_names:
        return [name.strip() for name in args.vm_names.split(",") if name.strip()]
    manifest = read_manifest(prefix)
    if not manifest:
        die(
            f"No manifest at {manifest_path(prefix)}. "
            "Run 'deploy' first or pass --vm-names a,b,c"
        )
    return manifest["vm_names"]


def cmd_provision_user(args: argparse.Namespace, ctx: dict[str, Any]) -> int:
    prefix = validate_prefix(args.prefix)
    vm_names = resolve_vm_names(args, prefix)
    if not vm_names:
        die(f"No VMs to provision for prefix '{prefix}'")

    print(
        f"Provisioning user '{args.username}' on {len(vm_names)} VM(s) "
        f"with prefix '{prefix}'"
    )
    template_id = find_template_id(
        ctx["session"], ctx["base"], ctx["project_id"], TEMPLATES["provision_user"]
    )
    jobs = [
        (
            name,
            {
                "vm_name": name,
                "new_username": args.username,
                "new_user_password": args.password,
            },
        )
        for name in vm_names
    ]
    results = run_parallel(
        jobs,
        ctx["session"],
        ctx["base"],
        ctx["project_id"],
        template_id,
        args.concurrency,
        args.wait,
        args.poll_interval,
        args.task_timeout,
        message=f"Bulk provision-user: prefix={prefix} user={args.username}",
    )
    return summarize(results)


def cmd_install_citrix(args: argparse.Namespace, ctx: dict[str, Any]) -> int:
    prefix = validate_prefix(args.prefix)
    vm_names = resolve_vm_names(args, prefix)
    if not vm_names:
        die(f"No VMs to install Citrix VDA on for prefix '{prefix}'")

    print(f"Installing Citrix VDA on {len(vm_names)} VM(s) with prefix '{prefix}'")
    template_id = find_template_id(
        ctx["session"], ctx["base"], ctx["project_id"], TEMPLATES["install_citrix"]
    )
    jobs = [(name, {"vm_name": name}) for name in vm_names]
    results = run_parallel(
        jobs,
        ctx["session"],
        ctx["base"],
        ctx["project_id"],
        template_id,
        args.concurrency,
        args.wait,
        args.poll_interval,
        args.task_timeout,
        message=f"Bulk install-citrix: prefix={prefix}",
    )
    return summarize(results)


def add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--semaphore-url",
        default=os.environ.get("SEMAPHORE_URL", "http://localhost:3000"),
    )
    p.add_argument(
        "--semaphore-admin",
        default=os.environ.get("SEMAPHORE_ADMIN", "admin"),
    )
    p.add_argument(
        "--semaphore-password",
        default=os.environ.get("SEMAPHORE_ADMIN_PASSWORD", "changeme"),
    )
    p.add_argument("--project-name", default="Orka Engine Orchestration")
    p.add_argument(
        "--wait",
        dest="wait",
        action="store_true",
        default=True,
        help="Poll until tasks reach a terminal state (default)",
    )
    p.add_argument(
        "--no-wait",
        dest="wait",
        action="store_false",
        help="Submit and exit without waiting for completion",
    )
    p.add_argument("--poll-interval", type=float, default=3.0)
    p.add_argument("--task-timeout", type=float, default=1800.0)
    p.add_argument("--concurrency", type=int, default=5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_deploy = sub.add_parser("deploy", help="Bulk-create VMs sharing a prefix")
    p_deploy.add_argument("--prefix", required=True)
    p_deploy.add_argument("--count", type=int, required=True)
    p_deploy.add_argument(
        "--vm-image", required=True, help="OCI URL for the base image"
    )
    p_deploy.add_argument("--cpu", type=int, default=2)
    p_deploy.add_argument("--memory", type=int, default=4096, help="RAM in MB")
    p_deploy.add_argument(
        "--public-image",
        dest="public_image",
        action="store_true",
        default=True,
        help="VM image is publicly accessible (default)",
    )
    p_deploy.add_argument(
        "--private-image",
        dest="public_image",
        action="store_false",
        help="VM image requires OCI credentials configured in Semaphore",
    )
    p_deploy.add_argument("--network-interface", default="")
    p_deploy.add_argument(
        "--random-length",
        type=int,
        default=8,
        help="Length of the random suffix (must be even, default 8)",
    )
    add_common_args(p_deploy)
    p_deploy.set_defaults(func=cmd_deploy)

    p_list = sub.add_parser("list", help="List VMs whose names start with the prefix")
    p_list.add_argument("--prefix", required=True)
    p_list.add_argument(
        "--show-output",
        action="store_true",
        default=True,
        help="Print task output (default)",
    )
    p_list.add_argument("--no-show-output", dest="show_output", action="store_false")
    add_common_args(p_list)
    p_list.set_defaults(func=cmd_list)

    p_manage = sub.add_parser("manage", help="Set state for all VMs with the prefix")
    p_manage.add_argument("--prefix", required=True)
    p_manage.add_argument(
        "--state", required=True, choices=["running", "stopped", "absent"]
    )
    add_common_args(p_manage)
    p_manage.set_defaults(func=cmd_manage)

    p_delete = sub.add_parser("delete", help="Delete all VMs with the prefix")
    p_delete.add_argument("--prefix", required=True)
    p_delete.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt",
    )
    add_common_args(p_delete)
    p_delete.set_defaults(func=cmd_delete)

    p_user = sub.add_parser(
        "provision-user",
        help="Provision a user on every VM in the manifest for the prefix",
    )
    p_user.add_argument("--prefix", required=True)
    p_user.add_argument("--username", required=True)
    p_user.add_argument("--password", required=True)
    p_user.add_argument(
        "--vm-names",
        default="",
        help="Comma-separated VM names; overrides the manifest if provided",
    )
    add_common_args(p_user)
    p_user.set_defaults(func=cmd_provision_user)

    p_citrix = sub.add_parser(
        "install-citrix",
        help="Install the Citrix VDA on every VM in the manifest for the prefix",
    )
    p_citrix.add_argument("--prefix", required=True)
    p_citrix.add_argument(
        "--vm-names",
        default="",
        help="Comma-separated VM names; overrides the manifest if provided",
    )
    add_common_args(p_citrix)
    p_citrix.set_defaults(func=cmd_install_citrix)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    base = args.semaphore_url.rstrip("/")
    session = requests.Session()
    login(session, base, args.semaphore_admin, args.semaphore_password)
    try:
        project_id = find_project_id(session, base, args.project_name)
        ctx = {"session": session, "base": base, "project_id": project_id}
        failures = args.func(args, ctx)
    finally:
        session.post(f"{base}/api/auth/logout")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
