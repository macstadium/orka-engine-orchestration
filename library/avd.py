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
    - "Cameron Roe (@cameronbroe)"
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


class AVDManager:
    def __init__(self, module):
        self.module = module
        self.name = module.params["name"]
        self.cpu = module.params["cpu"]
        self.memory = module.params["memory"]
        self.bridge_ip = module.params["bridge_ip"]
        self.android_home_path = module.params["android_home_path"]
        self.run_avd_path = module.params["run_avd_path"]
        self.log_path = module.params["log_path"]
        self.avdmanager_path = (
            f"{self.android_home_path}/cmdline-tools/latest/bin/avdmanager"
        )
        self.result = dict(changed=False)

    def avd_exists(self):
        """Check if an AVD exists by name using avdmanager."""
        return self.name in get_avd_list(avdmanager_path=self.avdmanager_path)

    def find_running_avd(self):
        """Find a running AVD by name. Returns (avd_info, all_running_avds)."""
        avd_list = get_running_avd_list(run_avd_path=self.run_avd_path)
        running_avd = next((avd for avd in avd_list if avd["name"] == self.name), None)
        return running_avd, avd_list

    def start(self):
        """Start an AVD. Returns the result dict."""
        if not self.avd_exists():
            self.module.fail_json(
                msg=f"AVD '{self.name}' does not exist", **self.result
            )

        env = os.environ.copy()
        env["PATH"] = (
            f"{self.android_home_path}/emulator:/opt/homebrew/bin:/opt/homebrew/sbin:"
            + env.get("PATH", "")
        )
        cmd = [self.run_avd_path, self.name]

        running_avd, avd_list = self.find_running_avd()

        if running_avd is not None:
            self.result["message"] = f"AVD {self.name} already running"
            self.result["avd_list"] = avd_list
            return self.result

        if self.cpu is not None:
            cmd.extend(["-c", str(self.cpu)])
        if self.memory is not None:
            cmd.extend(["-m", str(self.memory)])

        used_console_ports = {avd["relay_port"] - 10_001 for avd in avd_list}
        console_port = CONSOLE_PORT_START
        while console_port in used_console_ports:
            console_port += 2

        relay_port = (console_port + 1) + 10_000

        cmd.extend(
            ["-p", str(console_port), "-b", self.bridge_ip, "-r", str(relay_port)]
        )

        if self.module.check_mode:
            self.result["changed"] = True
            self.result["message"] = f"Would run AVD {self.name} with command: {cmd}"
            return self.result

        with open(f"{self.log_path}/{self.name}.log", "a") as log_file:
            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
                env=env,
            )

        self.result["changed"] = True
        self.result["process_id"] = proc.pid
        self.result["relay_ip"] = self.bridge_ip
        self.result["relay_port"] = relay_port
        return self.result

    def stop(self):
        """Stop a running AVD. Returns the result dict."""
        if not self.avd_exists():
            self.module.fail_json(
                msg=f"AVD '{self.name}' does not exist", **self.result
            )

        running_avd, _ = self.find_running_avd()

        if running_avd is None:
            self.result["message"] = f"AVD {self.name} is not running"
            return self.result

        if self.module.check_mode:
            self.result["changed"] = True
            self.result["message"] = (
                f"Would stop AVD {self.name} (PID {running_avd['pid']})"
            )
            return self.result

        os.kill(running_avd["pid"], signal.SIGTERM)

        self.result["changed"] = True
        self.result["process_id"] = running_avd["pid"]
        self.result["message"] = f"Stopped AVD {self.name} (PID {running_avd['pid']})"
        return self.result

    def delete(self):
        """Stop (if running) and delete an AVD. Returns the result dict."""
        if not self.avd_exists():
            self.result["message"] = f"AVD {self.name} does not exist"
            return self.result

        running_avd, _ = self.find_running_avd()
        stop_result = dict(changed=False)
        if running_avd is not None:
            stop_result = self.stop()

        if self.module.check_mode:
            self.result["changed"] = True
            self.result["message"] = f"Would delete AVD {self.name}"
            return self.result

        cmd = [self.avdmanager_path, "-s", "delete", "avd", "--name", self.name]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            self.module.fail_json(
                msg=f"Failed to delete AVD {self.name}: {proc.stderr}",
                **self.result,
            )

        self.result["changed"] = True
        self.result["message"] = f"Deleted AVD {self.name}"
        if stop_result.get("changed"):
            self.result["message"] = f"Stopped and deleted AVD {self.name}"
        return self.result

    def manage(self):
        """Manage the AVD based on the desired state."""
        state = self.module.params["state"]
        if state == "running":
            return self.start()
        elif state == "stopped":
            return self.stop()
        else:
            return self.delete()


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

    try:
        manager = AVDManager(module)
        result = manager.manage()
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=f"Failed to manage AVD {module.params['name']}: {e}")


if __name__ == "__main__":
    main()
