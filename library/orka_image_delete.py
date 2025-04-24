#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: orka_image_delete
short_description: Delete container images using orka-engine
description:
    - Delete container images from the local image store using the orka-engine CLI.
options:
    image_name:
        description:
            - The image bundle name to delete as visible in the `image list` subcommand.
            - For images that have tags, will default to the `latest` tag.
            - To specify a different tag, append the tag separated by a colon (e.g., ghcr.io/macstadium/example:some-other-tag).
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
    - This operation is irreversible and will permanently remove the image.
author:
    - Ivan Spasov (@ispasov)
'''

EXAMPLES = r'''
- name: Delete a local image
  orka_image_delete:
    image_name: orkaSequoia

- name: Delete a specific image tag
  orka_image_delete:
    image_name: ghcr.io/macstadium/example:v1.2.3
'''

RETURN = r'''
command:
    description: The command that was executed
    type: str
    returned: always
    sample: "orka-engine image delete orkaSequoia"
rc:
    description: The command return code
    type: int
    returned: always
    sample: 0
stdout:
    description: Standard output from the command
    type: str
    returned: always
    sample: "Image 'orkaSequoia' successfully deleted"
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
'''

from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
        argument_spec=dict(
        image_name=dict(type='str', required=True),
        binary_path=dict(type='str', required=False, default='/usr/local/bin/orka-engine')
    ),
        supports_check_mode=False
    )

    image_name = module.params['image_name']
    binary_path = module.params['binary_path']

    result = dict(
        changed=False,
        command='',
        rc=0,
        stdout='',
        stderr='',
    )

    cmd = [binary_path, 'image', 'delete', image_name]

    result['command'] = ' '.join(cmd)

    rc, stdout, stderr = module.run_command(cmd)
    result['rc'] = rc
    result['stdout'] = stdout
    result['stderr'] = stderr

    if rc == 0:
        result['changed'] = True
    else:
        module.fail_json(**result)

    module.exit_json(**result)

if __name__ == '__main__':
    main()
