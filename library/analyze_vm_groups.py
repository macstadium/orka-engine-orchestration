#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: analyze_vm_groups
short_description: Check if a VM with the given name exists across hosts
version_added: "1.0"
description:
    - This module checks whether a VM with the specified name exists on any host.
    - It determines whether a VM needs to be deployed.
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
    vm_name:
        description:
            - The exact VM name to look for.
        required: true
        type: str

author:
    - "Ivan Spasov (@ispasov)"
'''

EXAMPLES = r'''
- name: Check if VM exists
  analyze_vm_groups:
    hosts_data:
      - hostname: "host1.example.com"
        vms:
          - name: "my-vm"
          - name: "other-vm"
      - hostname: "host2.example.com"
        vms:
          - name: "another-vm"
    vm_name: "my-vm"
  register: group_result
'''

RETURN = r'''
hosts_group_data:
    description: Processed host data with VM counts for the specified name
    type: list
    returned: success
    sample: [
        {
            "hostname": "host1.example.com",
            "group_vms_count": 1,
            "group_vms": [
                {
                    "name": "my-vm",
                    "state": "running"
                }
            ]
        }
    ]
total_group_vms:
    description: Total number of VMs with the specified name (0 or 1)
    type: int
    returned: success
    sample: 1
vms_to_deploy:
    description: Number of VMs to deploy (1 if VM does not exist, 0 if it does)
    type: int
    returned: success
    sample: 0
vm_name:
    description: The VM name that was analyzed
    type: str
    returned: success
    sample: "my-vm"
desired_vms:
    description: The total number of VMs desired (always 1)
    type: int
    returned: success
    sample: 1
'''

from ansible.module_utils.basic import AnsibleModule

def filter_vm_by_name(vms, vm_name):
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
    desired_vms = 1

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

        group_vms = filter_vm_by_name(vms, vm_name)
        group_vms_count = len(group_vms)
        total_group_vms += group_vms_count

        host_data = {
            'hostname': hostname,
            'group_vms_count': group_vms_count,
            'group_vms': group_vms
        }

        hosts_group_data.append(host_data)

    vms_to_deploy = desired_vms - total_group_vms

    result = {
        'changed': False,
        'hosts_group_data': hosts_group_data,
        'total_group_vms': total_group_vms,
        'vms_to_deploy': vms_to_deploy,
        'vm_name': vm_name,
        'desired_vms': desired_vms
    }

    module.exit_json(**result)

if __name__ == '__main__':
    main()
