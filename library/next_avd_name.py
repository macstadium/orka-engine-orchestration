#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: next_avd_name
short_description: Determine the next AVD name for a VM
version_added: "1.0"
description:
    - Scans ~/.android/avd for existing AVD directories matching the pattern C({vm_name}-avd-{index}).
    - Returns the next available name by incrementing past the highest existing index.
    - If no AVDs exist for the VM, returns C({vm_name}-avd-0).
    - Gaps from deleted AVDs are not filled.

options:
    vm_name:
        description:
            - The VM name used as the AVD name prefix.
        required: true
        type: str
    avd_home:
        description:
            - Path to the AVD home directory.
        required: false
        type: str
        default: "~/.android/avd"
author:
    - "Cameron Roe"
"""

EXAMPLES = r"""
- name: Get next AVD name
  next_avd_name:
    vm_name: my-vm
  register: result

- name: Show next AVD name
  ansible.builtin.debug:
    msg: "{{ result.avd_name }}"
    # => my-vm-avd-0
"""

RETURN = r"""
avd_name:
    description: The next available AVD name
    type: str
    returned: success
    sample: "my-vm-avd-0"
index:
    description: The index assigned to this AVD
    type: int
    returned: success
    sample: 0
"""

import os
import re

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vm_name=dict(type="str", required=True),
            avd_home=dict(type="str", required=False, default="~/.android/avd"),
        ),
        supports_check_mode=True,
    )

    vm_name = module.params["vm_name"]
    avd_home = os.path.expanduser(module.params["avd_home"])

    pattern = re.compile(re.escape(vm_name) + r"-avd-(\d+)\.avd$")
    highest = -1
    if os.path.isdir(avd_home):
        for entry in os.listdir(avd_home):
            match = pattern.match(entry)
            if match:
                highest = max(highest, int(match.group(1)))

    next_index = highest + 1

    avd_name = f"{vm_name}-avd-{next_index}"

    module.exit_json(changed=False, avd_name=avd_name, index=next_index)


if __name__ == "__main__":
    main()
