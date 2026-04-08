#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: plan_avd_management
short_description: Plan the management of an AVD on a target host
version_added: "1.0"
description:
    - Finds the host running the specified VM using host data.
    - Resolves the AVD name from the VM name and optional AVD index.
    - If avd_index is not provided and only one AVD exists for the VM, defaults to it.
    - If avd_index is not provided and multiple AVDs exist, fails with an error.
    - Returns the target host, AVD name, and current running state.

options:
    hosts_data:
        description:
            - List of dictionaries containing host VM data.
            - Each dictionary must have 'hostname' and 'vms' keys.
        required: true
        type: list
        elements: dict
    avd_hosts_data:
        description:
            - List of dictionaries containing host AVD data.
            - Each dictionary must have 'hostname', 'all_avds', and 'running_avds' keys.
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
            - The index of the AVD to manage (e.g., 0 for vm-name-avd-0).
            - If omitted and only one AVD exists for the VM, it is used automatically.
            - If omitted and multiple AVDs exist, the module fails.
        required: false
        type: int
    desired_state:
        description:
            - The desired state of the AVD.
        required: false
        type: str
        choices: ['running', 'stopped', 'absent']
        default: "running"
author:
    - "Cameron Roe"
"""

EXAMPLES = r"""
- name: Plan AVD management with explicit index
  plan_avd_management:
    hosts_data: "{{ gather_host_facts_all_hosts_data }}"
    avd_hosts_data: "{{ gather_avd_facts_all_hosts_data }}"
    vm_name: "my-vm"
    avd_index: 0
  register: plan

- name: Plan AVD management with auto-detected index
  plan_avd_management:
    hosts_data: "{{ gather_host_facts_all_hosts_data }}"
    avd_hosts_data: "{{ gather_avd_facts_all_hosts_data }}"
    vm_name: "my-vm"
  register: plan

- name: Show plan
  ansible.builtin.debug:
    msg: "Will manage {{ plan.avd_name }} on {{ plan.target_host }} (currently {{ plan.avd_state }})"
"""

RETURN = r"""
target_host:
    description: The hostname where the VM was found
    type: str
    returned: success
    sample: "host1.example.com"
avd_name:
    description: The AVD name to manage
    type: str
    returned: success
    sample: "my-vm-avd-0"
vm_name:
    description: The VM name that was searched for
    type: str
    returned: success
    sample: "my-vm"
avd_state:
    description: The current state of the AVD (running, stopped, or absent)
    type: str
    returned: success
    sample: "running"
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


def find_avds_for_vm(avd_hosts_data, target_host, vm_name):
    """Find all AVDs matching a VM name on the target host."""
    prefix = f"{vm_name}-avd-"
    for host_info in avd_hosts_data:
        if host_info["hostname"] == target_host:
            all_avds = host_info.get("all_avds", [])
            return [avd for avd in all_avds if avd.startswith(prefix)]
    return []


def is_avd_running(avd_hosts_data, target_host, avd_name):
    """Check if an AVD is currently running on the target host."""
    for host_info in avd_hosts_data:
        if host_info["hostname"] == target_host:
            running_avds = host_info.get("running_avds", [])
            return any(avd["name"] == avd_name for avd in running_avds)
    return False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            hosts_data=dict(type="list", elements="dict", required=True),
            avd_hosts_data=dict(type="list", elements="dict", required=True),
            vm_name=dict(type="str", required=True),
            avd_index=dict(type="int", required=False, default=None),
            desired_state=dict(
                type="str",
                required=False,
                default="running",
                choices=["running", "stopped", "absent"],
            ),
        ),
        supports_check_mode=True,
    )

    hosts_data = module.params["hosts_data"]
    avd_hosts_data = module.params["avd_hosts_data"]
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

    matching_avds = find_avds_for_vm(avd_hosts_data, target_host, vm_name)

    if avd_index is not None:
        avd_name = f"{vm_name}-avd-{avd_index}"
    else:
        if len(matching_avds) > 1:
            module.fail_json(
                msg=(
                    f"Error: Multiple AVDs found for VM '{vm_name}' on host "
                    f"'{target_host}': {', '.join(matching_avds)}. "
                    f"Please specify an avd_index."
                )
            )
        elif len(matching_avds) == 0:
            module.fail_json(
                msg=(
                    f"Error: No AVDs found for VM '{vm_name}' on host "
                    f"'{target_host}'. Expected at least one AVD for this VM.'."
                )
            )
        else:
            avd_name = matching_avds[0] if matching_avds else f"{vm_name}-avd-0"

    if avd_name not in matching_avds:
        module.fail_json(
            msg=(
                f"Error: AVD '{avd_index}' does not exist for VM '{vm_name}' on "
                f"host '{target_host}'. Available AVDs: {', '.join(matching_avds)}."
            )
        )

    running = is_avd_running(avd_hosts_data, target_host, avd_name)
    avd_state = "running" if running else "stopped"

    module.exit_json(
        changed=False,
        target_host=target_host,
        avd_name=avd_name,
        vm_name=vm_name,
        avd_state=avd_state,
    )


if __name__ == "__main__":
    main()
