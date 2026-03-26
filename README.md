# Orka Engine Orchestration

This project provides an Ansible-based orchestration system for managing Orka VMs across multiple hosts. It allows you to plan and deploy VMs in a controlled manner, ensuring proper capacity management and distribution.

## Prerequisites

- Ansible installed on the control host
- Orka Engine License Key and URL to installer
- SSH access to remote hosts
- Python 3.x on both control and remote hosts
- sshpass installed on the control host for the Ansible runner

## Semaphore UI

A web-based UI for running playbooks is available via [Ansible Semaphore](https://semaphoreui.com/). This lets end users execute playbooks from a browser without needing CLI access. See [semaphore/README.md](semaphore/README.md) for setup instructions.

## Project Structure

```
├── deploy.yml               # Main deployment playbook
├── delete.yml               # Main deletion playbook
├── vm.yml                   # Main playbook for managing (delete, start, stop) a specific VM
├── pull_image.yml           # Main playbook for pulling an image on all hosts
├── create_image.yml         # Main playbook for creating an image and pushing it to a remote registry
├── list.yml                 # Main playbook for listing VMs
├── install-engine.yml       # Main playbook for installing Orka Engine
├── install_android_sdk.yml  # Main playbook for installing Android SDK
├── sdkmanager_install.yml   # Main playbook for installing Android SDK platforms and system images
├── sdkmanager_uninstall.yml # Main playbook for uninstalling Android SDK platforms and system images
├── create_avd.yml           # Main playbook for creating Android Virtual Devices
├── provision_user.yml       # Main playbook for provisioning an admin user on a VM
├── install_citrix_vda.yml   # Main playbook for installing Citrix VDA on a VM
├── register_citrix_vda.yml  # Main playbook for registering a Citrix VDA with a Delivery Controller
├── dev/                 # Development environment
│   ├── inventory        # Inventory file for development
│   └── group_vars/      # Test vars for development
```

## Setup

1. Create a development vars:

   ```bash
   mkdir -p dev/group_vars/all
   touch dev/group_vars/all/main.yml
   ```

2. Add `ansible_user` and `vm_image` to the variables

3. Create an inventory file in `dev/inventory` with your hosts:
   ```ini
   [hosts]
   host1_ip
   host2_ip
   ```

## Variables

- `vm_name`: Name of the VM to deploy or manage (required)
- `max_vms_per_host`: Maximum number of VMs allowed per host (default: defined in your inventory or group vars)
- `vm_image`: The image used to deploy VMs from
- `ansible_user`: The user used to connect to the Mac hosts
- `engine_binary`: Path to the Orka engine binary (default: defined in your inventory or group vars)
- `network_interface`: The network to attach the VM to, such as `en0` (default: none, will deploy via NAT mode)
- `cpu`: The number of vCPUs to allocate to a given VM (default: 2)
- `memory`: The amount of memory in MB to allocate to a given VM (default: 4096)

## Usage

### Installing Engine

To install Orka Engine run

```bash
ansible-playbook install_engine.yml -i dev/inventory -e "orka_license_key=<license_key>" -e "engine_url=<engine_url>"
```

where:

- `orka_license_key` - is the Engine license key
- `engine_url` - is the URL to download Engine from

**Note** - To force redeployment or upgrade pass `-e "install_engine_force=true"`.

### Installing Android SDK

To install the Android SDK (including Java JDK, command-line tools, and platform-tools) on target hosts:

```bash
ansible-playbook install_android_sdk.yml -i dev/inventory
```

This will:

- Install Eclipse Temurin JDK 21 (if not already present)
- Download and set up Android command-line tools
- Accept Android SDK licenses
- Install base SDK packages
- Configure `JAVA_HOME`, `ANDROID_HOME`, and `PATH` in the user's `.zshrc`

**Note** - To force reinstallation pass `-e "install_android_sdk_force=true"`.

### Installing Android SDK Platforms and System Images

To install an Android SDK platform and its system images on target hosts:

```bash
ansible-playbook sdkmanager_install.yml -i dev/inventory
```

This will:
- Verify that `sdkmanager` is available (requires the Android SDK to be installed first)
- Install the specified platform (default: `android-35`)
- Install system images for the specified image types (default: `default,google_apis`)

Optional variables:

- `platform` - The Android platform to install (default: `android-35`)
- `image_types` - Comma-separated list of system image types to install (default: `default,google_apis`)

Example with custom platform and image types:

```bash
ansible-playbook sdkmanager_install.yml -i dev/inventory -e "platform=android-34" -e "image_types=default,google_apis,google_apis_playstore"
```

### Uninstalling Android SDK Platforms and System Images

To uninstall an Android SDK platform and all of its system images from target hosts:

```bash
ansible-playbook sdkmanager_uninstall.yml -i dev/inventory
```

This will:
- Verify that `sdkmanager` is available
- Find and uninstall all system images for the specified platform
- Uninstall the platform itself

Optional variables:

- `platform` - The Android platform to uninstall (default: `android-35`)

Example:

```bash
ansible-playbook sdkmanager_uninstall.yml -i dev/inventory -e "platform=android-34"
```

### Creating an Android Virtual Device

Run the `create_avd.yml` playbook with `--tags plan` to see a plan for which hosts the AVD will be created on

```bash
ansible-playbook create_avd.yml -i dev/inventory -e "vm_name=my-vm" -e "avd_name=my-avd" --tags plan
```

Then, to actually create an Android Virtual Device (AVD) on the host where a specific VM is running:

```bash
ansible-playbook create_avd.yml -i dev/inventory -e "vm_name=my-vm" -e "avd_name=my-avd"
```

This will:
- Gather VM data from all hosts
- Find the host where the specified VM is running
- Create an AVD on that host only
- Verify that `avdmanager` is available (requires the Android SDK to be installed first)
- Skip creation if an AVD with the same name already exists

Required variables:

- `vm_name` - The name of the VM where the AVD should be created (must be running on one of the hosts)
- `avd_name` - The name of the AVD to create

Optional variables:

- `platform` - The Android platform to use (default: `android-35`)
- `image_type` - The system image type to use (default: `default`)
- `sdcard_size` - The SD card size for the AVD (default: `4096M`)

Example with custom settings:

```bash
ansible-playbook create_avd.yml -i dev/inventory -e "vm_name=my-vm" -e "avd_name=my-avd" -e "platform=android-34" -e "image_type=google_apis" -e "sdcard_size=8192M"
```

### Planning Deployment

To plan a deployment without actually creating VMs:

```bash
ansible-playbook deploy.yml -i dev/inventory -e "vm_name=my-vm" --tags plan
```

This will:

- Check capacity on all hosts
- Check if a VM with the given name already exists
- Create a deployment plan
- Display the plan without executing it

### Executing Deployment

To actually deploy the VM:

```bash
ansible-playbook deploy.yml -i dev/inventory -e "vm_name=my-vm" -e "vm_image=<image>"
```

### How It Works

1. **Capacity Check**: The system first checks the current capacity and running VMs on each host.
2. **Planning**: Creates a deployment plan. If a VM with the given name already exists, no new VM is deployed.
3. **Deployment**: Executes the deployment plan, creating the VM on the selected host.

### Planning Deletion

To plan a deletion without actually deleting a VM:

```bash
ansible-playbook delete.yml -i dev/inventory -e "vm_name=my-vm" --tags plan
```

This will:

- Check capacity on all hosts
- Find the VM with the given name
- Create a deletion plan
- Display the plan without executing it

### Executing Deletion

To actually delete the VM:

```bash
ansible-playbook delete.yml -i dev/inventory -e "vm_name=my-vm"
```

### How It Works

1. **Capacity Check**: The system first checks the current capacity and running VMs on each host.
2. **Planning**: Finds the VM by name and creates a deletion plan. The playbook fails if no VM with the given name is found.
3. **Deletion**: Executes the deletion plan, removing the VM from its host.

### Deleting a single VM

If you want to delete a single VM run:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=absent"
```

where `vm_name` is the name of the VM you want to delete. If can be a partial match.

**NOTE** - This playbook deletes all VMs matching the provided name. If you want to delete a VM on a specific host you need to use:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>"   -e "desired_state=absent" --limit <host>
```

where `host` is the host you want to delete a VM from.

### Stop a single VM

If you want to stop a VM run:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=stopped"
```

where `vm_name` is the full name or partial match of the VM or VMs you want to stop.

**NOTE** - This playbook stops all VMs matching that name. If you want to stop a VM on a specific host you need to use:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" --limit <host>
```

where `host` is the host you want to stop a VM from.

### Start a single VM

If you want to start a VM run:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=running"
```

where `vm_name` is matches name or names of the VM you want to start.

**NOTE** - This playbook starts all VM with that name. If you want to start a VM on a specific host you need to use:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=running" --limit <host>
```

where `host` is the host you want to start a VM from.

### Listing VMs by name

To find a specific VM matching a given name:

```bash
ansible-playbook list.yml -i dev/inventory -e "vm_name=my-vm"
```

You can also list all VMs across all hosts:

```bash
ansible-playbook list.yml -i dev/inventory
```

### Pull OCI image to hosts

To pull an OCI image to the hosts run:

```bash
ansible-playbook pull_image.yml -i dev/inventory -e "remote_image_name=<image_to_pull>"
```

where `image_to_pull` is the OCI image you want to pull. Optionally you could also specify the following variables:

- `registry_username` - The username to authenticate to the registry with
- `registry_password` - The password to authenticate to the registry with
- `insecure_pull` - Whether to allow pulling via HTTP

### Configure an OCI image and push it to a registry

This workflow:

1. Deploys a VM from a specified base image
2. Configures the VM by running all bash scripts inside the [scripts](/scripts) folder
3. Pushes an image from the VM to a specified remote OCI registry
4. Deletes the VM

**Note** By default, VMs are not accessible from outside of the host they are deployed on. To connect to the VMs and to configure them we use port forwarding. SSHPass is required on the Ansible runner in order to be able to connect to the VM.

To configure and image and push it to a remote registry:

1. Ensure you have added your bash scripts to the [scripts](/scripts) folder
2. Run

```bash
ansible-playbook create_image.yml -i dev/inventory -e "remote_image_name=<remote_destination>" -e "vm_image=<base_image>"
```

where `remote_destination` is the OCI image you want to push to. `base_image` is the image you want to deploy from. Optionally you could also specify the following variables:

- `registry_username` - The username to authenticate to the registry with
- `registry_password` - The password to authenticate to the registry with
- `insecure_push` - Whether to allow pushing via HTTP
- `upgrade_os` - Whether you want the OS to be upgraded as part of the image creation process

### Provisioning a user on a VM

To provision an admin user account on a running VM:

```bash
ansible-playbook provision_user.yml -i dev/inventory \
  -e "vm_name=<vm_name>" \
  -e "vm_username=<vm_username>" \
  -e "vm_password=<vm_password>" \
  -e "new_username=<new_username>" \
  -e "new_user_password=<new_user_password>"
```

where:

- `vm_name` - the exact name of the running VM to provision the user on
- `vm_username` - the existing admin username on the VM used to connect
- `vm_password` - the password for the existing admin user
- `new_username` - the username for the new account
- `new_user_password` - the password for the new account

The playbook is idempotent — if the user already exists it will skip creation.

**Note** — VMs may not be directly accessible from outside the host they run on,
depending on networking configuration. The playbook connects to the VM via SSH
through the Mac host as a jump proxy. `sshpass` must be installed on the Ansible
runner. Apple Command Line Tools will be installed on the VM automatically if not
already present.

### Installing Citrix VDA

To install Citrix Virtual Delivery Agent (VDA) on a running VM:

```bash
ansible-playbook install_citrix_vda.yml -i dev/inventory \
  -e "vm_name=<vm_name>" \
  -e "vm_username=<vm_username>" \
  -e "vm_password=<vm_password>" \
  -e "citrix_installer_url=<citrix_dmg_url>" \
  -e "hostname_suffix=<domain_suffix>"
```

where:

- `vm_name` - the exact name of the running VM to install Citrix VDA on (also used as the VM hostname)
- `vm_username` - the existing admin username on the VM used to connect
- `vm_password` - the password for the existing admin user
- `citrix_installer_url` - Download URL for the Citrix VDA `.dmg`. We recommend hosting your installer in an S3 bucket with a [presigned URL](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html).
- `hostname_suffix` - domain suffix appended to `vm_name` to form the full hostname (e.g. `corp.example.com`). This value can be blank to just use the VM name as the hostname.

This playbook:

1. Locates the VM by name across all hosts and adds it to the inventory via a jump proxy
2. Installs developer tools and .NET runtime prerequisites
3. Sets the VM hostname using the provided name and suffix
4. Downloads, mounts, and installs the Citrix VDA package
5. Grants required TCC permissions (screen capture and accessibility) for Citrix components when SIP is disabled
6. Reboots the VM to complete installation

**Note** — `sshpass` must be installed on the Ansible runner. The playbook connects to the VM via the Mac host as a jump proxy.

### Registering Citrix VDA with a Delivery Controller

After installing Citrix VDA, register the VM with a Citrix Delivery Controller using an enrollment token:

```bash
ansible-playbook register_citrix_vda.yml -i dev/inventory \
  -e "vm_name=<vm_name>" \
  -e "vm_username=<vm_username>" \
  -e "vm_password=<vm_password>" \
  -e "enrollment_token=<enrollment_token>"
```

where:

- `vm_name` - the exact name of the running VM to register
- `vm_username` - the existing admin username on the VM used to connect
- `vm_password` - the password for the existing admin user
- `enrollment_token` - Citrix enrollment token for registering the VDA with the Delivery Controller

# Best Practices for VM Management

You can group VMs together by having a shared prefix.
This will allow you to manage start, stop, and delete multiple
VMs across various nodes by running a single task in Semaphore, or
executing a single Ansible run from the command line.
