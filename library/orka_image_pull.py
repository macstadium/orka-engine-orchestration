#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: orka_image_pull
short_description: Pull container images using orka-engine
description:
    - Pull/download container images from an OCI registry using the orka-engine CLI.
    - Supports authentication, insecure registry connections, and cache cleaning.
options:
    remote_name:
        description:
            - The remote image name and reference in the format <registry-address>/<name>:<reference>.
            - The reference can be a tag or a manifest digest, with the default reference being 'latest'.
        required: true
        type: str
    local_name:
        description:
            - Image bundle name on local disk (e.g., orkaSequoia).
            - Acts as the path where the image will be stored, by default relative to the configured base directory.
            - If an absolute path is provided, it will ignore the base directory configuration.
            - If not provided, the local name will match the remote name.
        required: false
        type: str
    username:
        description:
            - The username used for authenticating with the image registry.
        required: false
        type: str
    password:
        description:
            - The password used for authenticating with the image registry.
        required: false
        type: str
    insecure:
        description:
            - Use HTTP instead of HTTPS for registry requests.
            - This is insecure and should only be used in trusted networks.
        required: false
        type: bool
        default: false
    clean_cache:
        description:
            - Free disk space if needed before pulling an image by removing images from the cache.
        required: false
        type: bool
        default: true
    binary_path:
        description:
            - Path to the orka-engine executable.
        required: false
        type: str
        default: orka-engine
notes:
    - This module requires the orka-engine tool to be installed on the target host.
author:
    - Ivan Spasov @(ispasov)
'''

EXAMPLES = r'''
- name: Pull latest version of an image
  orka_image_pull:
    remote_name: 0123456789.dkr.ecr.us-east-1.amazonaws.com/orka-image:latest

- name: Pull an image with registry authentication
  orka_image_pull:
    remote_name: private-registry.example.com/my-app:1.0.0
    username: registry_user
    password: "{{ registry_password }}"

- name: Pull image with custom local name
  orka_image_pull:
    remote_name: 0123456789.dkr.ecr.us-east-1.amazonaws.com/orka-image:latest
    local_name: my-custom-image
    clean_cache: false

- name: Pull from insecure registry
  orka_image_pull:
    remote_name: insecure-registry:5000/test-image:latest
    insecure: true
'''

RETURN = r'''
command:
    description: The command that was executed
    type: str
    returned: always
    sample: "orka-engine image pull --clean-cache 0123456789.dkr.ecr.us-east-1.amazonaws.com/orka-image:latest"
rc:
    description: The command return code
    type: int
    returned: always
    sample: 0
stdout:
    description: Standard output from the command
    type: str
    returned: always
    sample: "Image successfully pulled and stored as 'orka-image'"
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
        remote_name=dict(type='str', required=True),
        local_name=dict(type='str', required=False),
        username=dict(type='str', required=False, no_log=True),
        password=dict(type='str', required=False, no_log=True),
        insecure=dict(type='bool', required=False, default=False),
        clean_cache=dict(type='bool', required=False, default=True),
        binary_path=dict(type='str', required=False, default='/usr/local/bin/orka-engine')
    ),
        supports_check_mode=False
    )

    remote_name = module.params['remote_name']
    local_name = module.params['local_name']
    username = module.params['username']
    password = module.params['password']
    insecure = module.params['insecure']
    clean_cache = module.params['clean_cache']
    binary_path = module.params['binary_path']

    result = dict(
        changed=False,
        command='',
        rc=0,
        stdout='',
        stderr='',
    )

    cmd = [binary_path, 'image', 'pull']
    
    if insecure:
        cmd.append('--insecure')
    
    if username:
        cmd.extend(['--username', username])
    
    if password:
        cmd.extend(['--password', password])
    
    cmd.append(remote_name)
    
    if local_name:
        cmd.append(local_name)
    
    if clean_cache:
        cmd.append('--clean-cache')

    result['command'] = ' '.join(cmd)

    rc, stdout, stderr = module.run_command(cmd)
    result['rc'] = rc
    result['stdout'] = stdout
    result['stderr'] = stderr

    if rc != 0:
        module.fail_json(msg=f"Failed to pull image: {stderr}", **result)

    result['changed'] = True if "Image already up to date" not in stdout else False

    module.exit_json(**result)

if __name__ == '__main__':
    main()
