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


def _extract_flag_value(flag, args):
    """
    Extract the value following a flag in a list of command-line arguments.

    Args:
        flag: The flag to search for (e.g. "-b", "-r")
        args: List of command-line arguments to search

    Returns:
        str: The value immediately following the flag, or None if the flag
            is not present or has no subsequent value
    """
    if flag in args:
        flag_index = args.index(flag)
        if flag_index + 1 < len(args):
            return args[flag_index + 1]
    return None


def _parse_running_avd_process(line):
    """
    Parse a line of pgrep output into a running AVD info dict.

    Args:
        line: A single line of output from pgrep -fl

    Returns:
        dict: AVD info with keys: name, pid, gateway_ip, relay_port
    """
    parts = line.split()
    process_args = parts[3:]
    return {
        "name": parts[3],
        "pid": int(parts[0]),
        "gateway_ip": _extract_flag_value("-b", process_args),
        "relay_port": int(_extract_flag_value("-r", process_args)),
    }


def get_running_avd_list(run_avd_path="/opt/orka/bin/run-avd"):
    """
    Get list of running AVDs from the process table

    Args:
        run_avd_path: The path to the run-avd script

    Returns:
        list: The list of running AVDs with name, pid, gateway_ip, and relay_port for each
    """

    cmd = ["/usr/bin/pgrep", "-fl", run_avd_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode == 0:
        return [_parse_running_avd_process(line) for line in proc.stdout.splitlines()]
    elif proc.returncode == 1:
        return []
    else:
        raise RuntimeError(f"Failed to get running AVD list: {proc.stderr.strip()}")


def get_avd_list(avdmanager_path="avdmanager"):
    """
    Get list of all AVDs from the avdmanager

    Args:
        avdmanager_path: The path to the avdmanager binary
    Returns:
        list: The list of all AVDs on the host
    """
    cmd = [avdmanager_path, "list", "avd", "-c"]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode == 0:
        return [avd.strip() for avd in proc.stdout.splitlines() if avd.strip()]
    else:
        raise RuntimeError(f"Failed to get AVD list: {proc.stderr.strip()}")
