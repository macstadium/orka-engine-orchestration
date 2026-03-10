#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: plan_deletion
short_description: Select VMs by name or prefix for deletion
version_added: "1.0"
description:
    - This module selects VMs matching the specified name or prefix for deletion.
    - The output is a deletion plan that specifies which hosts the VMs should be deleted from.
    - The module fails if no matching VMs are found.

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
            - The name or prefix of VMs to delete.
            - Matches VMs whose name starts with this value.
        required: true
        type: str
author:
    - "Ivan Spasov (@ispasov)"
"""

EXAMPLES = r"""
- name: Select VMs to delete by prefix
  plan_deletion:
    hosts_data:
      - hostname: "host1.example.com"
        vms:
          - name: "my-vm-1"
          - name: "my-vm-2"
          - name: "other-vm"
      - hostname: "host2.example.com"
        vms:
          - name: "my-vm-3"
    vm_name: "my-vm"
  register: deletion_plan
"""

RETURN = r"""
deletion_plan:
    description: Dictionary mapping host names to a list of VM names to delete
    type: dict
    returned: success
    sample: {"host1.example.com": ["my-vm-1", "my-vm-2"], "host2.example.com": ["my-vm-3"]}
vms_selected:
    description: Total number of VMs selected for deletion
    type: int
    returned: success
    sample: 3
total_vms:
    description: Total number of matching VMs found
    type: int
    returned: success
    sample: 3
vm_name:
    description: The name or prefix that was searched for
    type: str
    returned: success
    sample: "my-vm"
hosts_with_vms:
    description: List of hosts that have matching VMs
    type: list
    returned: success
    sample: ["host1.example.com", "host2.example.com"]
"""

from ansible.module_utils.basic import AnsibleModule


def filter_vms_by_prefix(vms, vm_name):
    """Filter VMs whose name starts with the specified prefix."""
    return [
        vm
        for vm in vms
        if isinstance(vm, dict) and vm.get("name", "").startswith(vm_name)
    ]


def main():
    module = AnsibleModule(
        argument_spec=dict(
            hosts_data=dict(type="list", elements="dict", required=True),
            vm_name=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )

    hosts_data = module.params["hosts_data"]
    vm_name = module.params["vm_name"]

    for host_info in hosts_data:
        if not host_info.get("hostname"):
            module.fail_json(msg="Each host in hosts_data must have a 'hostname' key")
        if not isinstance(host_info.get("vms", []), list):
            module.fail_json(msg="The 'vms' key for each host must be a list")

    deletion_plan = {}
    hosts_with_vms = []

    for host_info in hosts_data:
        hostname = host_info.get("hostname")
        vms = host_info.get("vms", [])

        matching_vms = filter_vms_by_prefix(vms, vm_name)

        if matching_vms:
            hosts_with_vms.append(hostname)
            deletion_plan[hostname] = [vm.get("name") for vm in matching_vms]

    total_vms = sum(len(names) for names in deletion_plan.values())

    if total_vms == 0:
        module.fail_json(msg=f"Error: No VMs matching '{vm_name}' were found.")

    result = {
        "changed": False,
        "deletion_plan": deletion_plan,
        "vms_selected": total_vms,
        "total_vms": total_vms,
        "vm_name": vm_name,
        "hosts_with_vms": hosts_with_vms,
    }

    module.exit_json(**result)


if __name__ == "__main__":
    main()
