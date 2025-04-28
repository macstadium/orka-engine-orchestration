# Orka Engine Orchestration

This project provides an Ansible-based orchestration system for managing Orka VMs across multiple hosts. It allows you to plan and deploy VMs in a controlled manner, ensuring proper capacity management and distribution.

## Prerequisites

- Ansible installed on the control machine
- Orka Engine installed on all remote hosts
- SSH access to remote hosts
- Python 3.x on both control and remote machines

## Project Structure

```
├── deploy.yml           # Main deployment playbook
├── delete.yml           # Main deletion playbook
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

## Usage

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

### Listing VMs from a group

To list the VMs from a group:

```bash
ansible-playbook list.yml -i dev/inventory -e "vm_group=test"
```
