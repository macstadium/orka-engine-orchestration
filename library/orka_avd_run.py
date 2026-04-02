#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: orka_avd_run
short_description: Run an AVD (Android virtual device) on the host with connectivity to an Orka VM
description:
    - Runs an Android virtual device on the host using the Android SDK tools
    - Starts a socat relay between the emulator ADBD port and the vmnet bridge interface for the Orka VM network
options:
    name:
        description: Name of the Android virtual device
        required: true
        type: str
    cpu:
        description: Number of CPU cores to allocate
        required: false
        type: int
    memory:
        description: Amount of memory (in MB) to allocate
        required: false
        type: int
    audio:
        description: Enable audio for the Android virtual device
        required: false
        type: bool
        default: false
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
- name: Run AVD with specific CPU and memory requests
  orka_avd_run:
    name: "foo-avd-0"
    cpu: 4
    memory: 2048

- name: Run AVD with audio enabled
  orka_avd_run:
    name: "foo-avd-0"
    audio: true

- name: Run AVD with specific vmnet bridge interface IP
  orka_avd_run:
    name: "foo-avd-0"
    bridge_ip: 192.168.65.1
"""

RETURN = r"""
changed:
    description: Whether the task resulted in a change
    type: bool
    returned: always
process_id:
    description: Process ID of the run-avd script
    type: int
    returned: on success
relay_ip:
    description: The IP address that the AVD is accessible from within the Orka VM guest
    type: str
    returned: on success
relay_port:
    description: The port that the AVD is accessible from within the Orka VM guest
    type: int
    returned: on success
"""

import os
import subprocess
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orka_utils import get_running_avd_list

CONSOLE_PORT_START = 5554

def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            cpu=dict(type="int", required=False),
            memory=dict(type="int", required=False),
            audio=dict(type="bool", required=False, default=False),
            bridge_ip=dict(type="str", required=False, default="192.168.64.1"),
            android_home_path=dict(type="str", required=False, default="/opt/android-sdk"),
            run_avd_path=dict(type="str", required=False, default="/opt/orka/bin/run-avd"),
            log_path=dict(type="str", required=False, default="/opt/orka/logs/avd"),
        ),
        supports_check_mode=True,
    )

    name = module.params["name"]
    cpu = module.params["cpu"]
    memory = module.params["memory"]
    audio = module.params["audio"]
    bridge_ip = module.params["bridge_ip"]
    android_home_path = module.params["android_home_path"]
    run_avd_path = module.params["run_avd_path"]
    log_path = module.params["log_path"]

    env = os.environ.copy()
    env["PATH"] = f"{android_home_path}/emulator:/opt/homebrew/bin:/opt/homebrew/sbin:" + env.get("PATH", "")
    cmd = [run_avd_path, name]

    result=dict(changed=False)

    try:
        avd_list = get_running_avd_list(run_avd_path=run_avd_path)
        running_avd = next((avd for avd in avd_list if avd["name"] == name), None)

        if running_avd is not None:
            result["message"] = f"AVD {name} already running"
            result["avd_list"] = avd_list
            module.exit_json(**result)

        if cpu is not None:
            cmd.extend(["-c", str(cpu)])
        if memory is not None:
            cmd.extend(["-m", str(memory)])
        if audio:
            cmd.append("-a")

        console_port = CONSOLE_PORT_START
        for _ in avd_list:
            console_port += 2

        relay_port = (console_port + 1) + 10_000

        cmd.extend(["-p", str(console_port), "-b", bridge_ip, "-r", str(relay_port)])

        if module.check_mode:
            result["changed"] = True
            result["message"] = f"Would run AVD {name} with command: {cmd}"
            module.exit_json(**result)

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
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=f"Failed to run AVD {name}: {e}", **result)

if __name__ == "__main__":
    main()
