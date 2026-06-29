# Bulk VM Lifecycle

`semaphore/bulk_vm_lifecycle.py` drives the Semaphore UI REST API to manage groups of Orka VMs that share a common name prefix. It is intended for customers who need to spin up, configure, manage, or tear down many VMs at once without clicking through the UI for each one — including day-2 operations such as provisioning a user across the group and installing the Citrix VDA on every VM.

Every VM created by `deploy` is named `<prefix>-<random>` (e.g. `demo-a1b2c3d4`). The script tracks the names it generated in a manifest at `semaphore/.bulk_vms_<prefix>.json`, which later subcommands read to target the same set of VMs.

## Prerequisites

- A running Semaphore instance configured via [`README.md`](README.md) (the project, templates, inventory, and credentials must already be in place).
- [`uv`](https://docs.astral.sh/uv/) on the workstation that runs the script.
- Admin credentials for Semaphore (the script logs in over the REST API).

Credentials and URL can be supplied via flags, environment variables, or `semaphore/.env`:

```
SEMAPHORE_URL=http://localhost:3000
SEMAPHORE_ADMIN=admin
SEMAPHORE_ADMIN_PASSWORD=changeme
```

## Subcommands

| Subcommand | Purpose | Template invoked |
| --- | --- | --- |
| `deploy` | Provision N VMs with the prefix | `Virtual Machines \| Deploy VM` |
| `list` | Show VMs whose names start with the prefix | `Virtual Machines \| List VMs` |
| `manage` | Set every prefix-matched VM to `running`/`stopped`/`absent` | `Virtual Machines \| Manage VM` |
| `delete` | Convenience wrapper for `manage --state absent`; clears the manifest on success | `Virtual Machines \| Manage VM` |
| `provision-user` | Add a user to every VM tracked in the manifest | `Virtual Machines \| Provision User to VM` |
| `install-citrix` | Install the Citrix VDA on every VM tracked in the manifest | `VDI \| Install Citrix VDA` |

## Examples

### Provision 5 VMs

```bash
uv run semaphore/bulk_vm_lifecycle.py deploy \
    --prefix demo --count 5 \
    --vm-image oci://ghcr.io/example/base-image:latest \
    --cpu 4 --memory 8192
```

Each VM is named `demo-<8 hex chars>`. The names are written to `semaphore/.bulk_vms_demo.json`.

Pass `--private-image` if the OCI URL requires the credentials stored in the `OCI Credentials` environment. Use `--network-interface en0` to attach a host NIC instead of NAT.

### List the group

```bash
uv run semaphore/bulk_vm_lifecycle.py list --prefix demo
```

Runs the List VMs template with `vm_name=demo`; the underlying playbook treats `vm_name` as a regex anchor (`^demo`), so it returns every VM whose name starts with the prefix.

### Bulk start / stop

```bash
uv run semaphore/bulk_vm_lifecycle.py manage --prefix demo --state stopped
uv run semaphore/bulk_vm_lifecycle.py manage --prefix demo --state running
```

This is a single Semaphore task per call. The Manage VM playbook iterates every host and operates on each VM whose name begins with the prefix.

### Provision a user across the group

```bash
uv run semaphore/bulk_vm_lifecycle.py provision-user \
    --prefix demo \
    --username developer \
    --password 's3cret!'
```

Reads the manifest at `semaphore/.bulk_vms_demo.json` and submits one parallel `Provision User to VM` task per VM. The underlying playbook requires an exact `vm_name` match, so the manifest is required. If you need to target a different set, pass `--vm-names demo-a1b2c3d4,demo-e5f6a7b8`.

### Install the Citrix VDA across the group

```bash
uv run semaphore/bulk_vm_lifecycle.py install-citrix --prefix demo
```

Reads the manifest at `semaphore/.bulk_vms_demo.json` and submits one parallel `VDI | Install Citrix VDA` task per VM. The Citrix playbook also requires an exact `vm_name` match, so the manifest is required (or pass `--vm-names a,b,c`).

Prerequisites — both live in the `Base VM Credentials` Semaphore environment and are set via `configure_semaphore.py`:

- `citrix_installer_url` — download URL for the Citrix VDA `.dmg` (pass `--citrix-installer-url`, e.g. an S3 presigned URL)
- `hostname_suffix` — domain suffix appended to each VM name to form the full hostname (pass `--hostname-suffix`); may be empty

Each task installs developer-tools and .NET prerequisites, sets the VM hostname to `<vm_name><hostname_suffix>`, installs the VDA, and **reboots the VM** to complete installation. Allow ample time per task (the default `--task-timeout 1800` is usually enough; raise it for slow installer downloads) and lower `--concurrency` if your hosts cannot handle every VM rebooting at once.

After installation, register each VM with the Delivery Controller using the existing `VDI | Register Citrix VDA` template, since enrollment tokens are issued per machine and are not supported by this script.

### Tear the group down

```bash
uv run semaphore/bulk_vm_lifecycle.py delete --prefix demo
```

You are prompted to confirm before the request goes through. Pass `--yes` for non-interactive runs (e.g. CI). The manifest is removed once every task succeeds; if any task fails, the manifest is kept so you can re-run the delete.

## How task submission works

Each subcommand:

1. Logs in to Semaphore via `POST /api/auth/login`.
2. Resolves the project ID via `GET /api/projects`.
3. Resolves the template ID via `GET /api/project/{id}/templates`.
4. Submits one or more `POST /api/project/{id}/tasks` requests; the survey variables are JSON-encoded and sent in the `environment` field (the same wire format the Semaphore UI uses).
5. If `--wait` (the default), polls `GET /api/project/{id}/tasks/{task_id}` every `--poll-interval` seconds (default 3 s) until the task reaches `success`, `error`, or `stopped`, or `--task-timeout` (default 1800 s) elapses.
6. Logs out via `POST /api/auth/logout`.

The exit status is `0` if every task reaches `success` and non-zero otherwise. `--no-wait` submits tasks and exits immediately, exiting `0` once all submissions are accepted.

## Common flags

These apply to every subcommand:

| Flag | Default | Purpose |
| --- | --- | --- |
| `--semaphore-url` | `http://localhost:3000` (or `$SEMAPHORE_URL`) | Semaphore base URL |
| `--semaphore-admin` | `$SEMAPHORE_ADMIN` or `admin` | Admin username |
| `--semaphore-password` | `$SEMAPHORE_ADMIN_PASSWORD` or `changeme` | Admin password |
| `--project-name` | `Orka Engine Orchestration` | Project that owns the templates |
| `--wait` / `--no-wait` | `--wait` | Poll until terminal state, or return after submission |
| `--poll-interval` | `3.0` | Seconds between status polls |
| `--task-timeout` | `1800.0` | Per-task timeout in seconds |
| `--concurrency` | `5` | Parallel task submissions for `deploy`, `provision-user`, and `install-citrix` |

## Manifest format

`semaphore/.bulk_vms_<prefix>.json`:

```json
{
  "prefix": "demo",
  "created_at": "2026-06-04T18:00:00+00:00",
  "vm_names": [
    "demo-a1b2c3d4",
    "demo-e5f6a7b8"
  ]
}
```

Running `deploy` again with the same prefix merges new names into the existing list. `delete` removes the file only when every task succeeds. The manifest is a workstation-local record and is safe to delete by hand if you want to start clean (subsequent `manage`/`delete` calls fall back to server-side prefix matching).

## Operational notes

- Prefixes must match `^[a-z0-9][a-z0-9-]{0,30}[a-z0-9]$` to keep the resulting VM names valid.
- The random suffix uses `secrets.token_hex`, so it is unpredictable and unique per call.
- `deploy`, `provision-user`, and `install-citrix` parallelize submissions through a thread pool. Lower `--concurrency` if Semaphore or the underlying hosts become saturated.
- `manage` and `delete` are single Semaphore tasks; their wall-clock time scales with the number of matched VMs because the playbook loops over them inside one Ansible run.
- For routine cleanup, schedule a wrapper such as `cron`/CI that runs `delete --prefix <prefix> --yes --no-wait`.

## Troubleshooting

When a task ends in `error` or `stopped`, the script prints the last ~40 lines of the task's Ansible output together with a link to the task in the Semaphore UI (e.g. `http://localhost:3000/project/1/templates?t=42`). Open that link for the full log, including the playbook command line and every host's output.
