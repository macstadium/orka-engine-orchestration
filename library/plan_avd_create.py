#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: plan_avd_create
short_description: Creates a plan for creating an AVD on a host running a specific VM
version_added: "1.0"
description:
    - This module searches all hosts for a VM with the specified exact name.
    - Returns the hostname where the VM is running so AVD creation can be targeted to that host.
    - The module fails if the VM is not found on any host.

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
            - The exact name of the VM to find.
            - The AVD will be created on the host where this VM is running.
        required: true
        type: str
author:
    - "Cameron Roe"
"""

EXAMPLES = r"""
- name: Find host for AVD creation
  plan_avd_create:
    hosts_data:
      - hostname: "host1.example.com"
        vms:
          - name: "my-vm-1"
          - name: "my-vm-2"
      - hostname: "host2.example.com"
        vms:
          - name: "my-vm-3"
    vm_name: "my-vm-1"
  register: avd_create_result
"""

RETURN = r"""
target_host:
    description: The hostname where the VM was found
    type: str
    returned: success
    sample: "host1.example.com"
vm_name:
    description: The VM name that was searched for
    type: str
    returned: success
    sample: "my-vm-1"
"""

from ansible.module_utils.basic import AnsibleModule


def find_vm_host(hosts_data, vm_name):
    """Find the host running a VM with the exact given name."""
    for host_info in hosts_data:
        hostname = host_info["hostname"]
        vms = host_info["vms"] if host_info["vms"] is not None else []
        for vm in vms:
            if vm["name"] == vm_name:
                return hostname
    return None


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
        if "hostname" not in host_info:
            module.fail_json(msg="Each host in hosts_data must have a 'hostname' key")
        if "vms" not in host_info:
            module.fail_json(msg="Each host in hosts_data must have a 'vms' key")

    target_host = find_vm_host(hosts_data, vm_name)

    if target_host is None:
        module.fail_json(msg=f"Error: VM '{vm_name}' was not found on any host.")

    result = {
        "changed": False,
        "target_host": target_host,
        "vm_name": vm_name,
    }

    module.exit_json(**result)


if __name__ == "__main__":
    main()
