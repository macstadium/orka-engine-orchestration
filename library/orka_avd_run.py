#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import subprocess
from ansible.module_utils.basic import AnsibleModule

def get_running_avd_list(run_avd_path):
    cmd = ["/usr/bin/pgrep", "-fl", run_avd_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode == 0:
        return [line.split()[3] for line in proc.stdout.splitlines()]
    elif proc.returncode == 1:
        return []
    else:
        raise RuntimeError(f"Failed to get running AVD list: {proc.stderr.strip()}")

def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            android_home_path=dict(type="str", required=False, default="/opt/android-sdk"),
            run_avd_path=dict(type="str", required=False, default="/opt/orka/bin/run-avd"),
        ),
        supports_check_mode=False,
    )

    name = module.params["name"]
    android_home_path = module.params["android_home_path"]
    run_avd_path = module.params["run_avd_path"]

    env = os.environ.copy()
    env["PATH"] = f"{android_home_path}/emulator:/opt/homebrew/bin:/opt/homebrew/sbin:" + env.get("PATH", "")
    cmd = [run_avd_path, name]

    result=dict(changed=False)

    try:
        avd_list = get_running_avd_list(run_avd_path=run_avd_path)

        if name in avd_list:
            result["message"] = f"AVD {name} already running"
            result["avd_list"] = avd_list
            module.exit_json(**result)

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

        module.exit_json(changed=True, pid=proc.pid)
    except Exception as e:
        module.fail_json(msg=f"Failed to run AVD {name}: {e}")

if __name__ == "__main__":
    main()
