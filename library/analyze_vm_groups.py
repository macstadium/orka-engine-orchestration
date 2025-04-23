#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: analyze_vm_groups
short_description: Count and analyze VMs belonging to specific groups
version_added: "1.0"
description:
    - This module analyzes VM data to count and group VMs by their group prefix.
    - It determines how many VMs of a specific group are running on each host.
    - It calculates how many additional VMs need to be deployed to reach a desired count.
    - The output can be used as input for the plan_deployment module.

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
            - If not specified, all VMs will be counted without filtering by group.
        required: true
        type: str
    desired_vms:
        description:
            - The total number of VMs desired for this group across all hosts.
        required: true
        type: int

author:
    - "Ivan Spasov (@ispasov)"
'''

EXAMPLES = r'''
- name: Count VMs in webapp group
  analyze_vm_groups:
    hosts_data:
      - hostname: "host1.example.com"
        vms: 
          - name: "webapp-abc123"
          - name: "database-def456"
      - hostname: "host2.example.com"
        vms:
          - name: "webapp-ghi789"
    vm_group: "webapp"
    desired_vms: 5
  register: group_result
'''

RETURN = r'''
hosts_group_data:
    description: Processed host data with group VM counts
    type: list
    returned: success
    sample: [
        {
            "hostname": "host1.example.com",
            "group_vms_count": 1,
            "group_vms": ["webapp-abc123"]
        }
    ]
total_group_vms:
    description: Total number of VMs in the group already running
    type: int
    returned: success
    sample: 2
vms_to_deploy:
    description: Number of additional VMs needed to reach the desired count
    type: int
    returned: success
    sample: 3
vm_group:
    description: The name of the VM group that was analyzed
    type: str
    returned: success
    sample: "webapp"
desired_vms:
    description: The total number of VMs desired for this group
    type: int
    returned: success
    sample: 5
'''

from ansible.module_utils.basic import AnsibleModule

def filter_group_vms(vms, vm_group):
    group_vms = []
    for vm in vms:
        if isinstance(vm, dict) and vm.get('name', '').startswith(f"{vm_group}-"):
            group_vms.append(vm)
    return group_vms

def main():
    module = AnsibleModule(
        argument_spec=dict(
            hosts_data=dict(type='list', elements='dict', required=True),
            vm_group=dict(type='str', required=True),
            desired_vms=dict(type='int', required=True),
        ),
        supports_check_mode=True
    )
    
    hosts_data = module.params['hosts_data']
    vm_group = module.params['vm_group']
    desired_vms = module.params['desired_vms']
    
    for host_info in hosts_data:
        if not host_info.get('hostname'):
            module.fail_json(msg="Each host in hosts_data must have a 'hostname' key")
        if not isinstance(host_info.get('vms', []), list):
            module.fail_json(msg="The 'vms' key for each host must be a list")
    
    hosts_group_data = []
    total_group_vms = 0
    
    for host_info in hosts_data:
        hostname = host_info.get('hostname')
        vms = host_info.get('vms', [])
        
        group_vms = filter_group_vms(vms, vm_group)
        group_vms_names = [vm.get('name') for vm in group_vms]
        group_vms_count = len(group_vms)
        total_group_vms += group_vms_count
        
        host_data = {
            'hostname': hostname,
            'group_vms_count': group_vms_count,
            'group_vms': group_vms_names
        }
            
        hosts_group_data.append(host_data)
    
    if total_group_vms > desired_vms:
        module.fail_json(
            msg=f"Error: {total_group_vms} VMs of group '{vm_group}' are already running, "
                f"but only {desired_vms} were requested."
        )
    
    vms_to_deploy = desired_vms - total_group_vms
    
    result = {
        'changed': False,
        'hosts_group_data': hosts_group_data,
        'total_group_vms': total_group_vms,
        'vms_to_deploy': vms_to_deploy,
        'vm_group': vm_group,
        'desired_vms': desired_vms
    }
    
    module.exit_json(**result)

if __name__ == '__main__':
    main()
