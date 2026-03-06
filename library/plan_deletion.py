#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: plan_deletion
short_description: Select a VM by name for deletion
version_added: "1.0"
description:
    - This module selects a VM with the specified name for deletion.
    - The output is a deletion plan that specifies which host the VM should be deleted from.
    - The module fails if no VM with the given name is found.

options:
    hosts_data:
        description:
            - List of dictionaries containing host VM data.
            - Each dictionary must have 'hostname' and 'vms' keys.
            - 'vms' is a list of VM dictionaries, each containing at least a 'name' key.
        required: true
        type: list
        elements: dict
    vm_name:
        description:
            - The exact name of the VM to delete.
        required: true
        type: str
author:
    - "Ivan Spasov (@ispasov)"
'''

EXAMPLES = r'''
- name: Select VM to delete
  plan_deletion:
    hosts_data:
      - hostname: "host1.example.com"
        vms:
          - name: "my-vm"
          - name: "other-vm"
      - hostname: "host2.example.com"
        vms:
          - name: "another-vm"
    vm_name: "my-vm"
  register: deletion_plan
'''

RETURN = r'''
deletion_plan:
    description: Dictionary mapping host names to a list of VM names to delete
    type: dict
    returned: success
    sample: {"host1.example.com": ["my-vm"]}
vms_selected:
    description: Total number of VMs selected for deletion (0 or 1)
    type: int
    returned: success
    sample: 1
total_group_vms:
    description: Total number of VMs found with the specified name
    type: int
    returned: success
    sample: 1
vm_name:
    description: The name of the VM that was targeted
    type: str
    returned: success
    sample: "my-vm"
hosts_with_vms:
    description: List of hosts that have a VM with the specified name
    type: list
    returned: success
    sample: ["host1.example.com"]
'''

from ansible.module_utils.basic import AnsibleModule

def filter_vm_by_name(vms, vm_name):
    """Filter VMs that match the specified name exactly."""
    return [vm for vm in vms if isinstance(vm, dict) and vm.get('name') == vm_name]

def main():
    module = AnsibleModule(
        argument_spec=dict(
            hosts_data=dict(type='list', elements='dict', required=True),
            vm_name=dict(type='str', required=True),
        ),
        supports_check_mode=True
    )

    hosts_data = module.params['hosts_data']
    vm_name = module.params['vm_name']

    for host_info in hosts_data:
        if not host_info.get('hostname'):
            module.fail_json(msg="Each host in hosts_data must have a 'hostname' key")
        if not isinstance(host_info.get('vms', []), list):
            module.fail_json(msg="The 'vms' key for each host must be a list")

    all_matching_vms = []
    hosts_with_vms = []

    for host_info in hosts_data:
        hostname = host_info.get('hostname')
        vms = host_info.get('vms', [])

        matching_vms = filter_vm_by_name(vms, vm_name)

        if matching_vms:
            hosts_with_vms.append(hostname)
            for vm in matching_vms:
                all_matching_vms.append((hostname, vm))

    total_group_vms = len(all_matching_vms)

    if total_group_vms == 0:
        module.fail_json(
            msg=f"Error: No VM named '{vm_name}' was found."
        )

    selected_vms = all_matching_vms[:1]

    deletion_plan = {}
    for hostname, vm in selected_vms:
        if hostname not in deletion_plan:
            deletion_plan[hostname] = []
        deletion_plan[hostname].append(vm.get('name'))

    result = {
        'changed': False,
        'deletion_plan': deletion_plan,
        'vms_selected': len(selected_vms),
        'total_group_vms': total_group_vms,
        'vm_name': vm_name,
        'hosts_with_vms': hosts_with_vms
    }

    module.exit_json(**result)

if __name__ == '__main__':
    main()
