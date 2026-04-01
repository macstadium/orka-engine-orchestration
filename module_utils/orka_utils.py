#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import subprocess


def get_vm_info(module, name, binary_path, result):
    """
    Get information about a VM from orka-engine

    Args:
        module: The Ansible module instance
        name: Name of the VM to get info for
        binary_path: Path to the orka-engine binary
        result: The result dictionary to update in case of error

    Returns:
        dict: VM information or None if VM doesn't exist
    """
    list_cmd = [binary_path, "vm", "list", "-o", "json"]

    try:
        list_result = subprocess.run(
            list_cmd, check=True, capture_output=True, text=True
        )
        vm_list = json.loads(list_result.stdout)

        existing_vm = next((vm for vm in vm_list if vm["name"] == name), None)
        return existing_vm
    except subprocess.CalledProcessError as e:
        module.fail_json(msg=f"Failed to check existing VMs: {e.stderr}", **result)
    except json.JSONDecodeError:
        module.fail_json(msg="Failed to parse VM list output as JSON", **result)
    except Exception as e:
        module.fail_json(msg=f"Error checking existing VMs: {str(e)}", **result)

def get_running_avd_list(run_avd_path="/opt/orka/bin/run-avd"):
    cmd = ["/usr/bin/pgrep", "-fl", run_avd_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode == 0:
        return [{"name": p_info[3], "pid": p_info[0]} for line in proc.stdout.splitlines() for p_info in [line.split()]]
    elif proc.returncode == 1:
        return []
    else:
        raise RuntimeError(f"Failed to get running AVD list: {proc.stderr.strip()}")
