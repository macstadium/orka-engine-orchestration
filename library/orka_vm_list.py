#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: orka_vm_list
short_description: List VMs using Orka Engine
description:
    - List virtual machines using orka-engine
    - Executes 'orka-engine vm list' command and returns VM information in JSON format
    - Can filter for a specific VM by name
options:
    name:
        description: Name of a specific VM to list. If not provided, lists all VMs.
        required: false
        type: str
    binary_path:
        description: Path to the orka-engine binary
        required: false
        type: str
        default: "orka-engine"
author:
    - "Ivan Spasov (@ispasov)"
"""

EXAMPLES = r"""
- name: List all VMs
  orka_vm_list:
  register: vm_list

- name: List specific VM
  orka_vm_list:
    name: test_vm
  register: vm_info
"""

RETURN = r"""
vms:
    description: List of VMs and their details
    type: list
    elements: dict
    returned: always
    contains:
        cpu:
            description: Number of CPU cores
            type: int
            returned: always
        displayDPI:
            description: Display DPI setting
            type: int
            returned: always
        displayHeight:
            description: Display height in pixels
            type: int
            returned: always
        displayWidth:
            description: Display width in pixels
            type: int
            returned: always
        ip:
            description: IP address of the VM
            type: str
            returned: always
        macAddress:
            description: MAC address of the VM
            type: str
            returned: always
        memory:
            description: Memory allocation
            type: str
            returned: always
        metadata:
            description: VM metadata, if any
            type: dict
            returned: always
        name:
            description: Name of the VM
            type: str
            returned: always
        state:
            description: Current state of the VM
            type: str
            returned: always
"""

import json
import subprocess
from ansible.module_utils.basic import AnsibleModule


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=False),
            binary_path=dict(type="str", required=False, default="orka-engine"),
        ),
        supports_check_mode=False,
    )

    vm_name = module.params["name"]
    engine_binary = module.params["binary_path"]

    result = dict(
        changed=False,
        vms=[],
        command="",
    )

    cmd = [engine_binary, "vm", "list", "-o", "json"]
    if vm_name:
        cmd.append(vm_name)

    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        try:
            vms = json.loads(proc.stdout)

            if not isinstance(vms, list):
                module.fail_json(
                    msg="Expected list of VMs but got different data structure",
                    **result,
                )

            result["vms"] = vms
            if vm_name and len(vms) == 0:
                result["message"] = f"No VM found with name '{vm_name}'"

            module.exit_json(**result)
        except json.JSONDecodeError:
            module.fail_json(
                msg="Failed to parse VM list output as JSON",
                stdout=proc.stdout,
                **result,
            )
    except subprocess.CalledProcessError as e:
        module.fail_json(
            msg=f"Failed to list VMs: {e.stderr}",
            rc=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
            **result,
        )


def main():
    run_module()


if __name__ == "__main__":
    main()
