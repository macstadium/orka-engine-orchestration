# Semaphore UI

[Ansible Semaphore](https://semaphoreui.com/) provides a web interface for running the orchestration playbooks without CLI access.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (included with Docker Desktop)
- [uv](https://docs.astral.sh/uv/)

## Quick Start

1. Copy the example environment file and fill in your values:

   ```bash
   cp semaphore/.env.example semaphore/.env
   ```

2. Generate an encryption key and add it to `semaphore/.env`:

   ```bash
   head -c32 /dev/urandom | base64
   ```

3. Set your admin credentials in `semaphore/.env`.

4. Start Semaphore:

   ```bash
   docker compose up -d
   ```

5. Open http://localhost:3000 (or your configured `SEMAPHORE_PORT`) and log in with the admin credentials from your `.env` file.

6. Execute the following to properly configure the SSH key you've generated:

```bash
SEMAPHORE_ADMIN=$YOUR_ADMIN \
SEMAPHORE_ADMIN_PASSWORD=$YOUR_ADMIN_PASSWORD \
uv run ./semaphore/configure_semaphore.py --ssh-key-file $YOUR_KEY
```

Please review `configure_semaphore.py` for additional parameters that can be
passed during setup, including the default username and password for any custom
base image, and OCI registry credentials.

To configure or rotate OCI registry credentials independently (e.g. for ECR short-lived tokens):

```bash
OCI_USERNAME=$YOUR_USERNAME \
OCI_PASSWORD=$YOUR_PASSWORD \
uv run ./semaphore/update_oci_credentials.py
```

All task templates, the repository, and the inventory are pre-configured automatically on first launch via `semaphore/project-seed.json`.

## Task Templates

The following templates are available in the **Orka Engine Orchestration** project. Each template prompts for its required inputs via a form when you click **Run**.

| Template       | Playbook             | Survey Variables                                            |
| -------------- | -------------------- | ----------------------------------------------------------- |
| Deploy VMs     | `deploy.yml`         | `vm_name`, `vm_image`                                       |
| Delete VMs     | `delete.yml`         | `vm_name`                                                   |
| Manage VM      | `vm.yml`             | `vm_name`, `desired_state` (`running`, `stopped`, `absent`) |
| List VMs       | `list.yml`           | `vm_name` (optional)                                        |
| Pull Image     | `pull_image.yml`     | `remote_image_name`                                         |
| Install Engine | `install_engine.yml` | `orka_license_key`, `engine_url`                            |
| Create Image   | `create_image.yml`   | `remote_image_name`, `vm_image`                             |
| Push Image     | `push_image.yml`     | `vm_name`, `oci_url`                                        |

## Stopping Semaphore

```bash
docker compose down
```

To remove all data (database, task history):

```bash
docker compose down -v
```
