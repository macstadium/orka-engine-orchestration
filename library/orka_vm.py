#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: orka_vm
short_description: Manage Orka VMs using Orka Engine
description:
    - Manage virtual machine lifecycle using orka-engine
    - Controls VM power state (running or stopped)
    - Executes 'orka-engine vm start', 'orka-engine vm stop', or 'orka-engine vm delete' command with provided parameters
    - Idempotent: only changes state if the VM is not already in the desired state
options:
    name:
        description: Name of the VM to manage
        required: true
        type: str
    state:
        description: Desired state of the VM
        required: true
        type: str
        choices: ['running', 'stopped', 'absent']
    binary_path:
        description: Path to the orka-engine binary
        required: false
        type: str
        default: /usr/local/bin/orka-engine
    wait_timeout:
        description: Maximum time to wait for the desired state, in seconds
        required: false
        type: int
        default: 60
    network_interface:
        description: Network interface to use for the VM
        required: false
        type: str
author:
    - "Ivan Spasov (@ispasov)"
    - "Bob Elwell (@relwell)"
"""

EXAMPLES = r"""
- name: Start a VM
  orka_vm:
    name: test_vm
    state: running

- name: Start a VM with bridged networking
  orka_vm:
    name: test_vm
    state: running
    network_interface: en0

- name: Stop a VM with custom binary path
  orka_vm:
    name: test_vm
    state: stopped
    binary_path: /usr/local/bin/orka-engine
    
- name: Delete a VM
  orka_vm:
    name: test_vm
    state: absent
"""

RETURN = r"""
name:
    description: Name of the VM that was managed
    type: str
    returned: always
"""

import subprocess
import time
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orka_utils import get_vm_info


def wait_for_vm_state(module, name, desired_state, binary_path, result, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        current_vm = get_vm_info(module, name, binary_path, result)

        if not current_vm:
            if desired_state == "absent":
                return True
            module.fail_json(
                msg=f"VM '{name}' not found while waiting for state change", **result
            )

        current_state = current_vm.get("state")

        if (desired_state == "running" and current_state == "running") or (
            desired_state == "stopped" and current_state != "running"
        ):
            return True

        time.sleep(1)

    return False


def start_vm(
    module, name, binary_path, result, wait_timeout=60, network_interface=None
):
    start_cmd = [binary_path, "vm", "start", "-d", name]

    if network_interface:
        start_cmd.extend(["--net-interface", network_interface])

    result["command"] = " ".join(start_cmd)

    try:
        subprocess.run(start_cmd, check=True, capture_output=True, text=True)

        if not wait_for_vm_state(
            module, name, "running", binary_path, result, wait_timeout
        ):
            module.fail_json(msg=f"Timeout waiting for VM '{name}' to start", **result)
    except subprocess.CalledProcessError as e:
        module.fail_json(
            msg=f"Failed to start VM: {e.stderr}",
            rc=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
            **result,
        )


def stop_vm(module, name, binary_path, result, wait_timeout=60):
    stop_cmd = [binary_path, "vm", "stop", name]
    result["command"] = " ".join(stop_cmd)

    try:
        subprocess.run(stop_cmd, check=True, capture_output=True, text=True)

        if not wait_for_vm_state(
            module, name, "stopped", binary_path, result, wait_timeout
        ):
            module.fail_json(msg=f"Timeout waiting for VM '{name}' to stop", **result)
    except subprocess.CalledProcessError as e:
        module.fail_json(
            msg=f"Failed to stop VM: {e.stderr}",
            rc=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
            **result,
        )


def delete_vm(module, name, binary_path, result):
    delete_cmd = [binary_path, "vm", "delete", name]
    result["command"] = " ".join(delete_cmd)

    try:
        proc = subprocess.run(delete_cmd, check=True, capture_output=True, text=True)

        if "is running and could not be deleted" in proc.stdout.lower():
            module.fail_json(
                msg=f"VM '{name}' is running and could not be deleted",
                stdout=proc.stdout,
                stderr=proc.stderr,
                **result,
            )

        return True, f"VM '{name}' deleted successfully"
    except subprocess.CalledProcessError as e:
        if "could not be found" in e.stderr.lower():
            return False, f"VM '{name}' does not exist, nothing to delete"
        elif "is running and could not be deleted" in e.stderr.lower():
            module.fail_json(
                msg=f"VM '{name}' is running and could not be deleted",
                rc=e.returncode,
                stdout=e.stdout,
                stderr=e.stderr,
                **result,
            )
        else:
            module.fail_json(
                msg=f"Failed to delete VM: {e.stderr}",
                rc=e.returncode,
                stdout=e.stdout,
                stderr=e.stderr,
                **result,
            )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            state=dict(
                type="str", required=True, choices=["running", "stopped", "absent"]
            ),
            binary_path=dict(type="str", required=False, default="orka-engine"),
            wait_timeout=dict(type="int", required=False, default=60),
            network_interface=dict(type="str", required=False),
        ),
        supports_check_mode=True,
    )

    name = module.params["name"]
    desired_state = module.params["state"]
    binary_path = module.params["binary_path"]
    wait_timeout = module.params["wait_timeout"]
    network_interface = module.params["network_interface"]

    result = dict(
        changed=False,
        name=name,
        command="",
    )

    def exit_with_result(changed):
        result["changed"] = changed
        result["name"] = name
        module.exit_json(**result)

    existing_vm = get_vm_info(module, name, binary_path, result)

    if not existing_vm and desired_state == "absent":
        exit_with_result(
            False, "absent", f"VM '{name}' does not exist, nothing to delete"
        )

    if not existing_vm and desired_state != "absent":
        module.fail_json(msg=f"VM '{name}' does not exist", **result)

    current_state = existing_vm.get("state") if existing_vm else "absent"
    result["current_state"] = current_state

    if desired_state == "running" and current_state == "running":
        exit_with_result(False)
    elif desired_state == "stopped" and current_state != "running":
        exit_with_result(False)
    elif desired_state == "absent" and current_state == "absent":
        exit_with_result(False)

    if module.check_mode:
        exit_with_result(True)

    if desired_state == "running":
        start_vm(
            module,
            name,
            binary_path,
            result,
            wait_timeout=wait_timeout,
            network_interface=network_interface,
        )
    elif desired_state == "stopped":
        stop_vm(module, name, binary_path, result, wait_timeout)
    elif desired_state == "absent":
        if current_state == "running":
            stop_vm(module, name, binary_path, result, wait_timeout)

        delete_vm(module, name, binary_path, result)

    exit_with_result(True)


if __name__ == "__main__":
    main()
