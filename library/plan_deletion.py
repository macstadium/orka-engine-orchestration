#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: plan_deletion
short_description: Select VMs from a specific group for deletion
version_added: "1.0"
description:
    - This module selects a specified number of VMs from a group for deletion.
    - It selects the first N VMs found in the specified group.
    - The output is a deletion plan that specifies which VMs to delete on each host.
    - The module fails if the requested deletion count exceeds existing VMs.

options:
    hosts_data:
        description:
            - List of dictionaries containing host VM data.
            - Each dictionary must have 'hostname' and 'vms' keys.
            - 'vms' is a list of VM dictionaries, each containing at least a 'name' key.
        required: true
        type: list
        elements: dict
    vm_group:
        description:
            - The VM group name prefix for filtering VMs.
            - VMs belonging to this group are expected to have names starting with '{vm_group}-'.
        required: true
        type: str
    vms_to_delete:
        description:
            - The number of VMs to delete from the specified group.
        required: true
        type: int
author:
    - "Ivan Spasov (@ispasov)"
'''

EXAMPLES = r'''
- name: Select VMs to delete from webapp group
  plan_deletion:
    hosts_data:
      - hostname: "host1.example.com"
        vms: 
          - name: "webapp-abc123"
          - name: "database-def456"
      - hostname: "host2.example.com"
        vms:
          - name: "webapp-ghi789"
    vm_group: "webapp"
    vms_to_delete: 1
  register: deletion_plan
'''

RETURN = r'''
deletion_plan:
    description: Dictionary mapping host names to a list of VM names to delete on each
    type: dict
    returned: success
    sample: {"host1.example.com": ["webapp-abc123"], "host2.example.com": []}
vms_selected:
    description: Total number of VMs selected for deletion
    type: int
    returned: success
    sample: 1
total_group_vms:
    description: Total number of VMs in the group
    type: int
    returned: success
    sample: 2
group_name:
    description: The name of the VM group that was analyzed
    type: str
    returned: success
    sample: "webapp"
hosts_with_vms:
    description: List of hosts that have VMs from the specified group
    type: list
    returned: success
    sample: ["host1.example.com", "host2.example.com"]
'''

from ansible.module_utils.basic import AnsibleModule

def filter_group_vms(vms, vm_group):
    """Filter VMs that belong to the specified group."""
    return [vm for vm in vms if isinstance(vm, dict) and vm.get('name', '').startswith(f"{vm_group}-")]

def main():
    module = AnsibleModule(
        argument_spec=dict(
            hosts_data=dict(type='list', elements='dict', required=True),
            vm_group=dict(type='str', required=True),
            vms_to_delete=dict(type='int', required=True),
        ),
        supports_check_mode=True
    )
    
    hosts_data = module.params['hosts_data']
    vm_group = module.params['vm_group']
    vms_to_delete = module.params['vms_to_delete']
    
    for host_info in hosts_data:
        if not host_info.get('hostname'):
            module.fail_json(msg="Each host in hosts_data must have a 'hostname' key")
        if not isinstance(host_info.get('vms', []), list):
            module.fail_json(msg="The 'vms' key for each host must be a list")

    all_group_vms = [] 
    hosts_with_vms = []
    
    for host_info in hosts_data:
        hostname = host_info.get('hostname')
        vms = host_info.get('vms', [])
        
        group_vms = filter_group_vms(vms, vm_group)
        
        if group_vms:
            hosts_with_vms.append(hostname)
            for vm in group_vms:
                all_group_vms.append((hostname, vm))
    
    total_group_vms = len(all_group_vms)
    
    if vms_to_delete > total_group_vms:
        module.fail_json(
            msg=f"Error: Only {total_group_vms} VMs of group '{vm_group}' are running, "
                f"but {vms_to_delete} were requested for deletion."
        )
    
    if vms_to_delete <= 0:
        result = {
            'changed': False,
            'deletion_plan': {},
            'vms_selected': 0,
            'total_group_vms': total_group_vms,
            'group_name': vm_group,
            'hosts_with_vms': hosts_with_vms
        }
        module.exit_json(**result)
    
    selected_vms = all_group_vms[:vms_to_delete]
    
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
        'group_name': vm_group,
        'hosts_with_vms': hosts_with_vms
    }
    
    module.exit_json(**result)

if __name__ == '__main__':
    main()
