#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: orka_engine_activate
short_description: Activate Orka Engine with a license key
description:
    - This module activates the Orka Engine using a provided license key.
options:
    license_key:
        description:
            - The license key to activate Orka Engine.
        required: true
        type: str
author:
    - Ivan Spasov (@ispasov)
'''

EXAMPLES = r'''
- name: Activate Orka Engine
  orka_engine_activate:
    license_key: "XXXX-XXXX-XXXX-XXXX"
'''

RETURN = r'''
stdout:
    description: Standard output from the activation command.
    returned: always
    type: str
    sample: "License activated successfully."
stderr:
    description: Standard error output from the activation command.
    returned: always
    type: str
    sample: "Error: Invalid license key."
rc:
    description: Return code from the activation command.
    returned: always
    type: int
    sample: 0
'''

from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
        argument_spec=dict(
        license_key=dict(type='str', required=True),
        binary_path=dict(type='str', required=False, default='/usr/local/bin/orka-engine'),
    ),
        supports_check_mode=False
    )

    license_key = module.params['license_key']
    binary_path = module.params['binary_path']
    result = dict(
        changed=False,
        stdout='',
        stderr='',
        rc=0
    )

    cmd = [binary_path, 'activate', license_key]
    rc, stdout, stderr = module.run_command(cmd)
    result['rc'] = rc
    result['stdout'] = stdout
    result['stderr'] = stderr

    if rc != 0:
        module.fail_json(msg=f"Failed to activate engine: {stderr}", **result)

    result['changed'] = True
    module.exit_json(**result)

if __name__ == '__main__':
    main()
