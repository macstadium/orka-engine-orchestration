#!/usr/bin/python3
# -*- coding: utf-8 -*-

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
        ),
        supports_check_mode=False,
    )

    name = module.params["name"]
    cpu = module.params["cpu"]
    memory = module.params["memory"]
    audio = module.params["audio"]
    bridge_ip = module.params["bridge_ip"]
    android_home_path = module.params["android_home_path"]
    run_avd_path = module.params["run_avd_path"]

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

        with open(f"/opt/orka/logs/avd/{name}.log", "w") as log_file:
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
