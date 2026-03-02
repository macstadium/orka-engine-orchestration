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
├── deploy.yml           # Main deployment playbook
├── delete.yml           # Main deletion playbook
├── vm.yml               # Main playbook for managing (delete, start, stop) a specific VM
├── pull_image.yml       # Main playbook for pulling an image on all hosts
├── create_image.yml     # Main playbook for creating an image and pushing it to a remote registry
├── list.yml             # Main playbook for listing VMs
├── install-engine.yml   # Main playbook for installing Orka Engine
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

- `vm_group`: Name of the VM group to deploy (required)
- `desired_vms`: Total number of VMs desired in the group (required)
- `max_vms_per_host`: Maximum number of VMs allowed per host (default: defined in your inventory or group vars)
- `vm_image`: The image used to deploy VMs from
- `ansible_user`: The user used to connect to the Mac hosts
- `engine_binary`: Path to the Orka engine binary (default: defined in your inventory or group vars)
- `network_interface`: The network to attach the VM to, such as `en0` (default: none, will deploy via NAT mode)

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

### Planning Deployment

To plan a deployment without actually creating VMs:

```bash
ansible-playbook deploy.yml -i dev/inventory -e "vm_group=test" -e "desired_vms=1" --tags plan
```

This will:
- Check capacity on all hosts
- Analyze VM groups
- Create a deployment plan
- Display the plan without executing it

### Executing Deployment

To actually deploy the VMs:

```bash
ansible-playbook deploy.yml -i dev/inventory -e "vm_group=test" -e "desired_vms=1"
```

### How It Works

1. **Capacity Check**: The system first checks the current capacity and running VMs on each host.
2. **Planning**: Creates a deployment plan based on available capacity and desired VM count. **NOTE** The playbook deploys only the amount of VMs needed to reach the desired count.
3. **Deployment**: Executes the deployment plan, creating VMs across hosts according to the plan.

### Planning Deletion

To plan a deletion without actually deleting VMs:

```bash
ansible-playbook delete.yml -i dev/inventory -e "vm_group=test" -e "delete_count=1" --tags plan
```

This will:
- Check capacity on all hosts
- Analyze VM groups
- Create a deletion plan
- Display the plan without executing it

### Executing Deletion

To actually delete the VMs:

```bash
ansible-playbook delete.yml -i dev/inventory -e "vm_group=test" -e "delete_count=1"
```

### How It Works

1. **Capacity Check**: The system first checks the current capacity and running VMs on each host.
2. **Planning**: Creates a deletion plan based on available capacity and desired deletion count. **NOTE** The playbook fails if you want to delete more VMs than available.
3. **Deployment**: Executes the deletion plan, deleting VMs across hosts according to the plan.

### Deleting a single VM

If you want to delete a sinlge VM run:
```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=absent"
```

where `vm_name` is the name of the VM you want to delete.

**NOTE** - This playbook deletes all VM with that name. If you want to delete a VM on a specific host you need to use:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>"   -e "desired_state=absent" --limit <host>
```

where `host` is the host you want to delete a VM from.

### Stop a single VM

If you want to stop a sinlge VM run:
```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=stopped"
```

where `vm_name` is the name of the VM you want to stop.

**NOTE** - This playbook stops all VM with that name. If you want to stop a VM on a specific host you need to use:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" --limit <host>
```

where `host` is the host you want to stop a VM from.

### Start a single VM

If you want to start a sinlge VM run:
```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=running"
```

where `vm_name` is the name of the VM you want to start.

**NOTE** - This playbook starts all VM with that name. If you want to start a VM on a specific host you need to use:

```bash
ansible-playbook vm.yml -i dev/inventory -e "vm_name=<vm_name>" -e "desired_state=running" --limit <host>
```

where `host` is the host you want to start a VM from.

### Listing VMs from a group

To list the VMs from a group:

```bash
ansible-playbook list.yml -i dev/inventory -e "vm_group=test"
```

You can also list all VMs accross all hosts:

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
