#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: orka_image_list
short_description: List images using Orka Engine
description:
    - List images using orka-engine
    - Executes 'orka-engine image list' command and returns image information in JSON format
options:
    binary_path:
        description: Path to the orka-engine binary
        required: false
        type: str
        default: "orka-engine"
author:
    - "Robert Elwell"
"""

EXAMPLES = r"""
- name: List all images
  orka_image_list:
  register: image_list

- name: List all images with custom binary
  orka_image_list:
    binary_path: /usr/local/bin/orka-engine
  register: image_list
"""

RETURN = r"""
images:
    description: List of images and their details
    type: list
    elements: dict
    returned: always
    contains:
        image:
            description: Image name (registry path without tag)
            type: str
            returned: always
        tag:
            description: Image tag
            type: str
            returned: always
        imageID:
            description: Image content digest
            type: str
            returned: always
        size:
            description: Total image size on disk
            type: str
            returned: always
        spaceUsed:
            description: Actual disk space used
            type: str
            returned: always
"""

import json
import subprocess
from ansible.module_utils.basic import AnsibleModule


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            binary_path=dict(type="str", required=False, default="orka-engine"),
        ),
        supports_check_mode=False,
    )

    engine_binary = module.params["binary_path"]

    result = dict(
        changed=False,
        images=[],
        command="",
    )

    cmd = [engine_binary, "image", "list", "-o", "json"]
    result["command"] = " ".join(cmd)

    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        try:
            images = json.loads(proc.stdout)

            if not isinstance(images, list):
                module.fail_json(
                    msg="Expected list of images but got different data structure",
                    **result,
                )

            result["images"] = images
            module.exit_json(**result)
        except json.JSONDecodeError:
            module.fail_json(
                msg="Failed to parse image list output as JSON",
                stdout=proc.stdout,
                **result,
            )
    except subprocess.CalledProcessError as e:
        module.fail_json(
            msg=f"Failed to list images: {e.stderr}",
            rc=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
            **result,
        )


def main():
    run_module()


if __name__ == "__main__":
    main()
