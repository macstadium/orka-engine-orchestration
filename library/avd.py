#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: avd
short_description: Manage an AVD (Android virtual device) on the host with connectivity to an Orka VM
description:
    - Manages the lifecycle of an Android virtual device on the host
    - When state is 'running', starts the AVD using the Android SDK tools and sets up a socat relay
    - When state is 'stopped', terminates the running AVD process
    - When state is 'absent', stops the AVD if running and deletes it using avdmanager
    - Idempotent - does not start an already running AVD or stop an already stopped one
options:
    name:
        description: Name of the Android virtual device
        required: true
        type: str
    state:
        description: Desired state of the AVD
        required: false
        type: str
        choices: ['running', 'stopped', 'absent']
        default: "running"
    cpu:
        description: Number of CPU cores to allocate (only used when starting)
        required: false
        type: int
    memory:
        description: Amount of memory (in MB) to allocate (only used when starting)
        required: false
        type: int
    bridge_ip: The IP address of the vmnet bridge interface for the Orka VM network
        description:
        required: false
        type: str
        default: "192.168.64.1"
    android_home_path: Home path for the Android SDK
        description:
        required: false
        type: str
        default: "/opt/android-sdk"
    run_avd_path: Path for the run-avd script
        description:
        required: false
        type: str
        default: "/opt/orka/bin/run-avd"
    log_path: Path for the directory to store logs for the run-avd script
        description:
        required: false
        type: str
        default: "/opt/orka/logs/avd"
author:
    - "Spike Burton (@spikeburton)"
"""

EXAMPLES = r"""
- name: Run AVD
  avd:
    name: "foo-avd-0"

- name: Run AVD with specific CPU and memory requests
  avd:
    name: "foo-avd-0"
    state: running
    cpu: 4
    memory: 2048

- name: Run AVD with specific vmnet bridge interface IP
  avd:
    name: "foo-avd-0"
    bridge_ip: 192.168.65.1

- name: Stop AVD
  avd:
    name: "foo-avd-0"
    state: stopped

- name: Delete AVD
  avd:
    name: "foo-avd-0"
    state: absent
"""

RETURN = r"""
process_id:
    description: Process ID of the run-avd script
    type: int
    returned: changed
    sample: 13444
relay_ip:
    description: The IP address that the AVD is accessible from within the Orka VM guest
    type: str
    returned: changed
    sample: 192.168.64.1
relay_port:
    description: The port that the AVD is accessible from within the Orka VM guest
    type: int
    returned: changed
    sample: 15555
"""

import os
import signal
import subprocess
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orka_utils import get_avd_list, get_running_avd_list

CONSOLE_PORT_START = 5554


def avd_exists(name, android_home_path):
    """Check if an AVD exists by name using avdmanager."""
    avdmanager_path = f"{android_home_path}/cmdline-tools/latest/bin/avdmanager"
    return name in get_avd_list(avdmanager_path=avdmanager_path)


def find_running_avd(name, run_avd_path):
    """Find a running AVD by name. Returns (avd_info, all_running_avds)."""
    avd_list = get_running_avd_list(run_avd_path=run_avd_path)
    running_avd = next((avd for avd in avd_list if avd["name"] == name), None)
    return running_avd, avd_list


def start_avd(
    module, name, cpu, memory, bridge_ip, android_home_path, run_avd_path, log_path
):
    """Start an AVD. Returns the result dict."""
    result = dict(changed=False)

    if not avd_exists(name, android_home_path):
        module.fail_json(msg=f"AVD '{name}' does not exist", **result)

    env = os.environ.copy()
    env["PATH"] = (
        f"{android_home_path}/emulator:/opt/homebrew/bin:/opt/homebrew/sbin:"
        + env.get("PATH", "")
    )
    cmd = [run_avd_path, name]

    running_avd, avd_list = find_running_avd(name, run_avd_path)

    if running_avd is not None:
        result["message"] = f"AVD {name} already running"
        result["avd_list"] = avd_list
        return result

    if cpu is not None:
        cmd.extend(["-c", str(cpu)])
    if memory is not None:
        cmd.extend(["-m", str(memory)])

    used_console_ports = {avd["relay_port"] - 10_001 for avd in avd_list}
    console_port = CONSOLE_PORT_START
    while console_port in used_console_ports:
        console_port += 2

    relay_port = (console_port + 1) + 10_000

    cmd.extend(["-p", str(console_port), "-b", bridge_ip, "-r", str(relay_port)])

    if module.check_mode:
        result["changed"] = True
        result["message"] = f"Would run AVD {name} with command: {cmd}"
        return result

    with open(f"{log_path}/{name}.log", "a") as log_file:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
            env=env,
        )

    result["changed"] = True
    result["process_id"] = proc.pid
    result["relay_ip"] = bridge_ip
    result["relay_port"] = relay_port
    return result


def stop_avd(module, name, run_avd_path, android_home_path):
    """Stop a running AVD. Returns the result dict."""
    result = dict(changed=False)

    if not avd_exists(name, android_home_path):
        module.fail_json(msg=f"AVD '{name}' does not exist", **result)

    running_avd, _ = find_running_avd(name, run_avd_path)

    if running_avd is None:
        result["message"] = f"AVD {name} is not running"
        return result

    if module.check_mode:
        result["changed"] = True
        result["message"] = f"Would stop AVD {name} (PID {running_avd['pid']})"
        return result

    os.kill(running_avd["pid"], signal.SIGTERM)

    result["changed"] = True
    result["process_id"] = running_avd["pid"]
    result["message"] = f"Stopped AVD {name} (PID {running_avd['pid']})"
    return result


def delete_avd(module, name, run_avd_path, android_home_path):
    """Stop (if running) and delete an AVD. Returns the result dict."""
    result = dict(changed=False)

    if not avd_exists(name, android_home_path):
        result["message"] = f"AVD {name} does not exist"
        return result

    running_avd, _ = find_running_avd(name, run_avd_path)
    stop_result = dict(changed=False)
    if running_avd is not None:
        stop_result = stop_avd(module, name, run_avd_path, android_home_path)

    if module.check_mode:
        result["changed"] = True
        result["message"] = f"Would delete AVD {name}"
        return result

    avdmanager_path = f"{android_home_path}/cmdline-tools/latest/bin/avdmanager"
    cmd = [avdmanager_path, "-s", "delete", "avd", "--name", name]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        module.fail_json(
            msg=f"Failed to delete AVD {name}: {proc.stderr}",
            **result,
        )

    result["changed"] = True
    result["message"] = f"Deleted AVD {name}"
    if stop_result.get("changed"):
        result["message"] = f"Stopped and deleted AVD {name}"
    return result


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            state=dict(
                type="str",
                required=False,
                default="running",
                choices=["running", "stopped", "absent"],
            ),
            cpu=dict(type="int", required=False),
            memory=dict(type="int", required=False),
            bridge_ip=dict(type="str", required=False, default="192.168.64.1"),
            android_home_path=dict(
                type="str", required=False, default="/opt/android-sdk"
            ),
            run_avd_path=dict(
                type="str", required=False, default="/opt/orka/bin/run-avd"
            ),
            log_path=dict(type="str", required=False, default="/opt/orka/logs/avd"),
        ),
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]

    try:
        if state == "running":
            result = start_avd(
                module,
                name,
                cpu=module.params["cpu"],
                memory=module.params["memory"],
                bridge_ip=module.params["bridge_ip"],
                android_home_path=module.params["android_home_path"],
                run_avd_path=module.params["run_avd_path"],
                log_path=module.params["log_path"],
            )
        elif state == "stopped":
            result = stop_avd(
                module,
                name,
                run_avd_path=module.params["run_avd_path"],
                android_home_path=module.params["android_home_path"],
            )
        else:
            result = delete_avd(
                module,
                name,
                run_avd_path=module.params["run_avd_path"],
                android_home_path=module.params["android_home_path"],
            )

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=f"Failed to manage AVD {name}: {e}")


if __name__ == "__main__":
    main()
