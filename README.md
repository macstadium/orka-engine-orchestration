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
├── install_android_sdk.yml    # Main playbook for installing Android SDK
├── uninstall_android_sdk.yml  # Main playbook for uninstalling Android SDK and tooling
├── sdkmanager_install.yml     # Main playbook for installing Android SDK platforms and system images
├── sdkmanager_uninstall.yml   # Main playbook for uninstalling Android SDK platforms and system images
├── deploy_avd.yml           # Main playbook for creating and running Android Virtual Devices
├── list_avd_profiles.yml # Main playbook for listing available AVD device profiles
├── list_avds.yml            # Main playbook for listing Android Virtual Devices
├── delete_avd.yml           # Main playbook for deleting Android Virtual Devices
├── avd.yml                  # Main playbook for managing (start, stop, delete) Android Virtual Devices
├── validate.yml             # Main playbook for validating engine, SDK, and image setup
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

### Hosts

#### Install Engine

To install Orka Engine run

```bash
ansible-playbook install_engine.yml -i dev/inventory -e "orka_license_key=<license_key>" -e "engine_url=<engine_url>"
```

where:

- `orka_license_key` - is the Engine license key
- `engine_url` - is the URL to download Engine from

**Note** - To force redeployment or upgrade pass `-e "install_engine_force=true"`.

#### Install Android SDK

To install the Android SDK and AVD runtime tooling on target hosts:

```bash
ansible-playbook install_android_sdk.yml -i dev/inventory
```

This will:

- Install Homebrew (if not already present) and ensure `brew shellenv` is loaded in `.zprofile`
- Install Eclipse Temurin JDK 21 (if not already present)
- Download and set up Android command-line tools at `/opt/android-sdk/cmdline-tools/latest/`
- Accept Android SDK licenses
- Install base SDK packages (`platform-tools`, `emulator`)
- Configure `JAVA_HOME`, `ANDROID_HOME`, and `PATH` in the user's `.zshrc`
- Install `socat` via Homebrew (used to relay ADB connections to AVDs)
- Create `/opt/orka/bin/` and `/opt/orka/logs/avd/` directories
- Install the `run-avd` script at `/opt/orka/bin/run-avd`

**Note** - To force reinstallation pass `-e "install_android_sdk_force=true"`.

#### Uninstall Android SDK

To remove the Android SDK and AVD runtime tooling from target hosts. This is the inverse of `install_android_sdk.yml`:

```bash
ansible-playbook uninstall_android_sdk.yml -i dev/inventory
```

This will:

- Remove the `run-avd` script at `/opt/orka/bin/run-avd`
- Remove the AVD log directory at `/opt/orka/logs/avd/`
- Uninstall `socat` via Homebrew
- Remove the `JAVA_HOME` / `ANDROID_HOME` / `PATH` block from the user's `.zshrc`
- Remove the Android SDK directory at `/opt/android-sdk`
- Remove the Eclipse Temurin JDK 21 installation

Homebrew itself is left in place since it may be used by other tooling on the host. To remove Homebrew as well, uncomment the relevant tasks at the bottom of the playbook.

#### Install Android SDK Platforms and System Images

To install an Android SDK platform and its system images on target hosts:

```bash
ansible-playbook sdkmanager_install.yml -i dev/inventory
```

This will:
- Verify that `sdkmanager` is available (requires the Android SDK to be installed first)
- Install the specified platform (default: `android-36`)
- Install system images for the specified image types (default: `default,google_apis`)

Optional variables:

- `platform` - The Android platform to install (default: `android-36`)
- `image_types` - Comma-separated list of system image types to install (default: `default,google_apis`)

Example with custom platform and image types:

```bash
ansible-playbook sdkmanager_install.yml -i dev/inventory -e "platform=android-34" -e "image_types=default,google_apis,google_apis_playstore"
```

#### Uninstall Android SDK Platforms and System Images

To uninstall an Android SDK platform and all of its system images from target hosts:

```bash
ansible-playbook sdkmanager_uninstall.yml -i dev/inventory
```

This will:
- Verify that `sdkmanager` is available
- Find and uninstall all system images for the specified platform
- Uninstall the platform itself

Optional variables:

- `platform` - The Android platform to uninstall (default: `android-36`)

Example:

```bash
ansible-playbook sdkmanager_uninstall.yml -i dev/inventory -e "platform=android-34"
```

### Virtual Machines

#### Deploy VM

To plan a deployment without actually creating VMs:

```bash
ansible-playbook deploy.yml -i dev/inventory -e "vm_name=my-vm" --tags plan
```

This will:

- Check capacity on all hosts
- Check if a VM with the given name already exists
- Create a deployment plan
- Display the plan without executing it

To actually deploy the VM:

```bash
ansible-playbook deploy.yml -i dev/inventory -e "vm_name=my-vm" -e "vm_image=<image>"
```

**How It Works**

1. **Capacity Check**: The system first checks the current capacity and running VMs on each host.
2. **Planning**: Creates a deployment plan. If a VM with the given name already exists, no new VM is deployed.
3. **Deployment**: Executes the deployment plan, creating the VM on the selected host.

#### Delete VM

To plan a deletion without actually deleting a VM:

```bash
ansible-playbook delete.yml -i dev/inventory -e "vm_name=my-vm" --tags plan
```

This will:

- Check capacity on all hosts
- Find the VM with the given name
- Create a deletion plan
- Display the plan without executing it

To actually delete the VM:

```bash
ansible-playbook delete.yml -i dev/inventory -e "vm_name=my-vm"
```

**How It Works**

1. **Capacity Check**: The system first checks the current capacity and running VMs on each host.
2. **Planning**: Finds the VM by name and creates a deletion plan. The playbook fails if no VM with the given name is found.
3. **Deletion**: Executes the deletion plan, removing the VM from its host.

#### Manage VM

To manage (start, stop, or delete) a VM:

```bash
# Delete a VM
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=absent"

# Stop a VM
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=stopped"

# Start a VM
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=running"
```

where `vm_name` is the full name or partial match of the VM(s) you want to manage.

**NOTE** - This playbook acts on all VMs matching the provided name. If you want to target a VM on a specific host, use `--limit`:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=absent" --limit <host>
```

#### List VMs

To find a specific VM matching a given name:

```bash
ansible-playbook list.yml -i dev/inventory -e "vm_name=my-vm"
```

You can also list all VMs across all hosts:

```bash
ansible-playbook list.yml -i dev/inventory
```

#### Provision User

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

### Images

#### Pull Image

To pull an OCI image to the hosts run:

```bash
ansible-playbook pull_image.yml -i dev/inventory -e "remote_image_name=<image_to_pull>"
```

where `image_to_pull` is the OCI image you want to pull. Optionally you could also specify the following variables:

- `registry_username` - The username to authenticate to the registry with
- `registry_password` - The password to authenticate to the registry with
- `insecure_pull` - Whether to allow pulling via HTTP

#### Create Image

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

### Android

#### Create and Run AVD

Run the `deploy_avd.yml` playbook with `--tags plan` to see a plan for which host the AVD will be created on:

```bash
ansible-playbook deploy_avd.yml -i dev/inventory -e "vm_name=my-vm" --tags plan
```

Then, to create an Android Virtual Device (AVD) on the host where a specific VM is running:

```bash
ansible-playbook deploy_avd.yml -i dev/inventory -e "vm_name=my-vm"
```

The AVD name is derived automatically from the VM name using the pattern `{vm_name}-avd-{index}`, where the index increments for each new AVD associated with the VM (e.g. `my-vm-avd-0`, `my-vm-avd-1`).

This will:
- Gather VM data from all hosts
- Find the host where the specified VM is running
- Determine the next available AVD index for the VM
- Create an AVD on that host only
- Verify that `avdmanager` is available (requires the Android SDK to be installed first)
- Run the AVD and setup network connectivity between the specified VM and the AVD

Required variables:

- `vm_name` - The name of the VM where the AVD should be created (must be running on one of the hosts)

Optional variables:

- `platform` - The Android platform to use (default: `android-36`)
- `image_type` - The system image type to use (default: `google_apis`)
- `device_profile` - Hardware device profile to emulate, e.g. `pixel_9` (default: `pixel_9`).
- `run_avd` - Whether to run the AVD after creation (default: `true`)
- `cpu`: The number of vCPUs to allocate when running the AVD (default: let host decide)
- `memory`: The amount of memory in MB to allocate when running the AVD (default: let host decide)

Example with custom settings:

```bash
ansible-playbook deploy_avd.yml -i dev/inventory -e "vm_name=my-vm" -e "platform=android-34" -e "image_type=google_apis" -e "device_profile=pixel_9" -e "cpu=4" -e "memory=2048"
```

#### Delete AVD

To delete an AVD from the host where a specific VM is running:

```bash
ansible-playbook delete_avd.yml -i dev/inventory -e "vm_name=my-vm" -e "avd_index=0"
```

The AVD name is derived from the VM name and index (e.g. `avd_index=0` deletes `my-vm-avd-0`).

This will:
- Gather VM data from all hosts
- Find the host where the specified VM is running
- Verify the AVD exists
- Check that no emulator is currently running for the AVD
- Delete the AVD

Required variables:

- `vm_name` - The name of the VM where the AVD is located
- `avd_index` - The index of the AVD to delete (e.g. `0` for `my-vm-avd-0`)

#### Manage AVD

To start, stop, or delete an AVD associated with a VM:

```bash
ansible-playbook avd.yml -i dev/inventory -e "vm_name=my-vm" -e "desired_state=running"
```

This will:
- Gather VM and AVD data from all hosts
- Find the host where the specified VM is running
- Resolve the target AVD (auto-detected when only one exists for the VM)
- Start, stop, or delete the AVD based on the desired state

The playbook is idempotent — it will not attempt to start an already running AVD, stop an already stopped one, or delete one that does not exist.

Required variables:

- `vm_name` - The name of the VM where the AVD is located
- `desired_state` - Target state: `running`, `stopped`, or `absent`

Optional variables:

- `avd_index` - The index of the AVD to manage (e.g. `0` for `my-vm-avd-0`). Required when multiple AVDs exist for the VM; defaults to the only AVD when there is just one.
- `cpu` - The number of vCPUs to allocate when starting the AVD
- `memory` - The amount of memory in MB to allocate when starting the AVD

Examples:

```bash
# Start the AVD for my-vm with custom resources
ansible-playbook avd.yml -i dev/inventory -e "vm_name=my-vm" -e "desired_state=running" -e "cpu=4" -e "memory=2048"

# Stop the AVD
ansible-playbook avd.yml -i dev/inventory -e "vm_name=my-vm" -e "desired_state=stopped"

# Delete a specific AVD by index
ansible-playbook avd.yml -i dev/inventory -e "vm_name=my-vm" -e "desired_state=absent" -e "avd_index=1"
```

To preview the plan without making changes:

```bash
ansible-playbook avd.yml -i dev/inventory -e "vm_name=my-vm" -e "desired_state=running" --tags plan
```

#### List AVDs

To list all AVDs across all hosts:

```bash
ansible-playbook list_avds.yml -i dev/inventory
```

To list only AVDs belonging to a specific VM:

```bash
ansible-playbook list_avds.yml -i dev/inventory -e "vm_name=my-vm"
```

Each AVD is displayed with its host and status. Running AVDs include additional details: PID, gateway IP, and ADB relay port.

Optional variables:

- `vm_name` - Filter by VM name (only shows AVDs matching `{vm_name}-avd-*`)

#### List AVD Device Profiles

To list all hardware device profiles available for AVD creation:

```bash
ansible-playbook list_avd_profiles.yml -i dev/inventory
```

This runs `avdmanager list device` on the first available host and displays all device IDs that can be passed as `device_profile` when creating an AVD.

### Validation

#### Validate Setup

The `validate.yml` playbook performs idempotent checks against target hosts to confirm the engine, Android SDK, SDK components, and OCI images are installed correctly. It uses `ansible.builtin.stat` and `ansible.builtin.command` rather than ad-hoc shell commands, which makes it safe to run alongside (or as part of) CI workflows.

To run all validation checks:

```bash
ansible-playbook validate.yml -i dev/inventory
```

The playbook is tag-aware so you can run subsets that match each phase of the setup sequence:

| Command | What it checks |
|---------|----------------|
| `ansible-playbook validate.yml -i dev/inventory --skip-tags sdk-components,images` | Engine binary + Android SDK base install (sdkmanager, Java, run-avd, socat) |
| `ansible-playbook validate.yml -i dev/inventory --tags sdk-components` | Android platform and system images installed via `sdkmanager_install.yml` |
| `ansible-playbook validate.yml -i dev/inventory --tags images` | OCI image is present in the engine image list |

**Checks performed:**

- Engine binary at `/usr/local/bin/orka-engine`
- `sdkmanager` at `/opt/android-sdk/cmdline-tools/latest/bin/sdkmanager`
- Java at `/Library/Java/JavaVirtualMachines/temurin-21.jre/Contents/Home/bin/java`
- `run-avd` script at `/opt/orka/bin/run-avd`
- `socat` at `/opt/homebrew/bin/socat`
- Platform directory at `/opt/android-sdk/platforms/<platform>` (tagged `sdk-components`)
- System image directories at `/opt/android-sdk/system-images/<platform>/<image_type>/arm64-v8a` for each image type (tagged `sdk-components`)
- OCI image list contains an expected substring (tagged `images`)

Optional variables:

- `platform` - Android platform to check for (default: `android-36`)
- `image_types` - Comma-separated list of system image types to check for (default: `default,google_apis`)
- `image_name` - Substring to look for in the engine's image list output (default: `sequoia`). Use this when validating against a custom image. Supports `name:tag` format — both parts are matched independently against the engine's image list output.

Example with custom values:

```bash
ansible-playbook validate.yml -i dev/inventory --tags sdk-components -e "platform=android-34" -e "image_types=default,google_apis_playstore"
ansible-playbook validate.yml -i dev/inventory --tags images -e "image_name=ghcr.io/myorg/my-image:1.0"
```

### VDI

#### Install Citrix VDA

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

#### Register Citrix VDA

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

## Best Practices for VM Management

You can group VMs together by having a shared prefix.
This will allow you to manage start, stop, and delete multiple
VMs across various nodes by running a single task in Semaphore, or
executing a single Ansible run from the command line.
