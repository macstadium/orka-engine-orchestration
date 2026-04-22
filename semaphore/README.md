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

Note that the `CITRIX_INSTALLER_URL` may store a URL that expires in a short time period, such as a
[presigned URL for an S3 bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html).
You can manually update this value on the [Variable Groups](http://localhost:3000/project/1/environment)
page by updating the appropriate field in the "Base VM Credentials" group.

## Task Templates

The following templates are available in the **Orka Engine Orchestration** project. Each template prompts for its required inputs via a form when you click **Run**.

| Template | Playbook | Survey Variables |
| --- | --- | --- |
| Android \| Create and Run Android Virtual Device | `deploy_avd.yml` | `vm_name`, `platform` (optional), `image_type` (optional), `device_profile` (optional), `run_avd` (optional), `cpu` (optional), `memory` (optional) |
| Android \| Delete Android Virtual Device | `delete_avd.yml` | `vm_name`, `avd_index` |
| Android \| List AVD Device Profiles | `list_avd_profiles.yml` | _(none)_ |
| Android \| List Android Virtual Devices | `list_avds.yml` | `vm_name` (optional) |
| Android \| Manage Android Virtual Device | `avd.yml` | `vm_name`, `desired_state` (`running`, `stopped`, `absent`), `avd_index` (optional), `cpu` (optional), `memory` (optional) |
| Hosts \| Install Android SDK | `install_android_sdk.yml` | `install_android_sdk_force` (optional) |
| Hosts \| Install Android SDK Components | `sdkmanager_install.yml` | `platform`, `image_types` (optional) |
| Hosts \| Install Engine | `install_engine.yml` | `orka_license_key`, `engine_url` |
| Hosts \| Uninstall Android SDK Components | `sdkmanager_uninstall.yml` | `platform` |
| Images \| Create Image | `create_image.yml` | `remote_image_name`, `vm_image` |
| Images \| Delete Image | `delete_image.yml` | `image_name`, `node_name` (optional) |
| Images \| List Images | `list_images.yml` | `node_name` (optional) |
| Images \| Pull Image | `pull_image.yml` | `remote_image_name` |
| Images \| Push Image | `push_image.yml` | `vm_name`, `oci_url` |
| VDI \| Install Citrix VDA | `install_citrix_vda.yml` | `vm_name` |
| VDI \| Register Citrix VDA | `register_citrix_vda.yml` | `vm_name`, `enrollment_token` |
| Virtual Machines \| Delete VM | `delete.yml` | `vm_name` |
| Virtual Machines \| Deploy VM | `deploy.yml` | `vm_name`, `vm_image`, `public_image` (optional), `cpu` (optional), `memory` (optional), `network_interface` (optional) |
| Virtual Machines \| List VMs | `list.yml` | `vm_name` (optional) |
| Virtual Machines \| Manage VM | `vm.yml` | `vm_name`, `desired_state` (`running`, `stopped`, `absent`) |
| Virtual Machines \| Provision User to VM | `provision_user.yml` | `vm_name`, `new_username`, `new_user_password` |

## Stopping Semaphore

```bash
docker compose down
```

To remove all data (database, task history):

```bash
docker compose down -v
```
