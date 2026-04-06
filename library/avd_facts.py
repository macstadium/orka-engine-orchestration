#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: avd_facts
short_description: Gather AVD facts for the current host
version_added: "1.0"
description:
    - Collects the list of all AVDs and all running AVDs on the host.
    - Sets `avd_facts_all` and `avd_facts_running` as Ansible facts.

options:
    avdmanager_path:
        description:
            - Path to the avdmanager binary.
        required: false
        type: str
        default: "avdmanager"
    run_avd_path:
        description:
            - Path to the run-avd script used to detect running AVDs.
        required: false
        type: str
        default: "/opt/orka/bin/run-avd"
author:
    - "Cameron Roe"
"""

EXAMPLES = r"""
- name: Gather AVD facts
  avd_facts:
    avdmanager_path: /opt/android-sdk/cmdline-tools/latest/bin/avdmanager

- name: Show all AVDs
  ansible.builtin.debug:
    var: avd_facts_all

- name: Show running AVDs
  ansible.builtin.debug:
    var: avd_facts_running
"""

RETURN = r"""
ansible_facts:
    description: Facts set by the module
    type: dict
    returned: success
    contains:
        avd_facts_all:
            description: List of all AVD names on the host
            type: list
            elements: str
            sample: ["my-vm-avd-0", "my-vm-avd-1"]
        avd_facts_running:
            description: List of running AVDs with name, pid, gateway_ip, and relay_port for each
            type: list
            elements: dict
            sample: [{"name": "my-vm-avd-0", "pid": "12345", "gateway_ip": "192.168.64.1", "relay_port": "15555"}]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orka_utils import get_avd_list, get_running_avd_list


def main():
    module = AnsibleModule(
        argument_spec=dict(
            avdmanager_path=dict(type="str", required=False, default="avdmanager"),
            run_avd_path=dict(
                type="str", required=False, default="/opt/orka/bin/run-avd"
            ),
        ),
        supports_check_mode=True,
    )

    avdmanager_path = module.params["avdmanager_path"]
    run_avd_path = module.params["run_avd_path"]

    try:
        all_avds = get_avd_list(avdmanager_path=avdmanager_path)
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    try:
        running_avds = get_running_avd_list(run_avd_path=run_avd_path)
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    module.exit_json(
        changed=False,
        ansible_facts=dict(
            avd_facts_all=all_avds,
            avd_facts_running=running_avds,
        ),
    )


if __name__ == "__main__":
    main()
