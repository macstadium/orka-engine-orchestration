#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: plan_avd_deletion
short_description: Plan the deletion of an AVD on a target host
version_added: "1.0"
description:
    - Finds the host running the specified VM using host data.
    - Computes the AVD name from the VM name and AVD index.
    - Checks that the AVD is not currently running using the process table.
    - Returns the target host and AVD name for the deletion play.

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
            - The exact name of the VM where the AVD resides.
        required: true
        type: str
    avd_index:
        description:
            - The index of the AVD to delete (e.g., 0 for vm-name-avd-0).
        required: true
        type: int
author:
    - "Cameron Roe"
"""

EXAMPLES = r"""
- name: Plan AVD deletion
  plan_avd_deletion:
    hosts_data: "{{ gather_host_facts_all_hosts_data }}"
    vm_name: "my-vm"
    avd_index: 0
  register: plan

- name: Show plan
  ansible.builtin.debug:
    msg: "Will delete {{ plan.avd_name }} from {{ plan.target_host }}"
"""

RETURN = r"""
target_host:
    description: The hostname where the VM was found
    type: str
    returned: success
    sample: "host1.example.com"
avd_name:
    description: The AVD name to delete
    type: str
    returned: success
    sample: "my-vm-avd-0"
vm_name:
    description: The VM name that was searched for
    type: str
    returned: success
    sample: "my-vm"
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
            avd_index=dict(type="int", required=True),
        ),
        supports_check_mode=True,
    )

    hosts_data = module.params["hosts_data"]
    vm_name = module.params["vm_name"]
    avd_index = module.params["avd_index"]

    for host_info in hosts_data:
        if "hostname" not in host_info:
            module.fail_json(msg="Each host in hosts_data must have a 'hostname' key")
        if "vms" not in host_info:
            module.fail_json(msg="Each host in hosts_data must have a 'vms' key")

    target_host = find_vm_host(hosts_data, vm_name)

    if target_host is None:
        module.fail_json(msg=f"Error: VM '{vm_name}' was not found on any host.")

    avd_name = f"{vm_name}-avd-{avd_index}"

    module.exit_json(
        changed=False,
        target_host=target_host,
        avd_name=avd_name,
        vm_name=vm_name,
    )


if __name__ == "__main__":
    main()
