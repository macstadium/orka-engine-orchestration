#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: orka_vm_save
short_description: Save a VM as an image using orka-engine
description:
    - Save a new image from an existing virtual machine to the local image store using orka-engine CLI.
    - Creates an image snapshot of the current VM state.
options:
    vm_name:
        description:
            - The name of the virtual machine to save as an image.
        required: true
        type: str
    image_name:
        description:
            - The name to give the saved image.
        required: true
        type: str
    binary_path:
        description:
            - Path to the orka-engine executable.
        required: false
        type: str
        default: orka-engine
notes:
    - This module requires the orka-engine tool to be installed on the target host.
    - The VM must exist and be in a valid state to be saved.
author:
    - Ivan Spasov (@ispasov)
"""

EXAMPLES = r"""
- name: Save VM state as an image
  orka_vm_save:
    vm_name: production-vm
    image_name: prod-backup-20250423
"""

RETURN = r"""
command:
    description: The command that was executed
    type: str
    returned: always
    sample: "orka-engine vm save production-vm prod-backup-20250423"
rc:
    description: The command return code
    type: int
    returned: always
    sample: 0
stdout:
    description: Standard output from the command
    type: str
    returned: always
    sample: "VM successfully saved as image 'prod-backup-20250423'"
stderr:
    description: Standard error from the command
    type: str
    returned: always
    sample: ""
changed:
    description: Whether the task resulted in a change
    type: bool
    returned: always
    sample: true
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vm_name=dict(type="str", required=True),
            image_name=dict(type="str", required=True),
            binary_path=dict(
                type="str", required=False, default="/usr/local/bin/orka-engine"
            ),
        ),
        supports_check_mode=False,
    )

    vm_name = module.params["vm_name"]
    image_name = module.params["image_name"]
    binary_path = module.params["binary_path"]

    result = dict(
        changed=False,
        command="",
        rc=0,
        stdout="",
        stderr="",
    )

    cmd = [binary_path, "vm", "save", vm_name, image_name]

    result["command"] = " ".join(cmd)

    rc, stdout, stderr = module.run_command(cmd)
    result["rc"] = rc
    result["stdout"] = stdout
    result["stderr"] = stderr

    if rc == 0:
        result["changed"] = True
    else:
        module.fail_json(msg=f"Failed to save VM as image: {stderr}", **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
