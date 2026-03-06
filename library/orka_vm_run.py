#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: orka_vm_run
short_description: Create and run a VM using Orka Engine
description:
    - Create and run a virtual machine using the orka-engine command line tool
    - Executes 'orka-engine vm run' command with provided parameters
options:
    name:
        description: Name of the VM to create
        required: true
        type: str
    image:
        description: Image to use for the VM
        required: true
        type: str
    detached:
        description: Run the VM in detached mode
        required: false
        type: bool
        default: true
    cpu:
        description: Number of CPU cores to allocate
        required: false
        type: int
        default: 2
    memory:
        description: Amount of memory (in MB) to allocate
        required: false
        type: int
        default: 4096
    network_interface:
        description: Network interface to use for the VM
        required: false
        type: str
    binary_path:
        description: Path to the orka-engine binary
        required: false
        type: str
        default: "orka-engine"
author:
    - "Ivan Spasov (@ispasov)"
    - "Bob Elwell (@relwell)"
'''

EXAMPLES = r'''
- name: Create and run a VM
  orka_vm_run:
    name: test_vm
    image: ghcr.io/macstadium/orka-images/sonoma:latest

- name: Create VM with custom resources
  orka_vm_run:
    name: custom_vm
    image: ghcr.io/macstadium/orka-images/sonoma:latest
    cpu: 4
    memory: "8192M"
    detached: true

- name: Create VM with specific network interface
  orka_vm_run:
    name: network_vm
    image: ghcr.io/macstadium/orka-images/sonoma:latest
    network_interface: en0
'''

RETURN = r'''
name:
    description: Name of the VM
    type: str
    returned: always
process_id:
    description: Process ID of the VM if successfully created
    type: int
    returned: on success
'''

import subprocess
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orka_utils import get_vm_info

def run_module():
    module = AnsibleModule(
        argument_spec=dict(
        name=dict(type='str', required=True),
        image=dict(type='str', required=True),
        detached=dict(type='bool', required=False, default=True),
        cpu=dict(type='int', required=False, default=2),
        memory=dict(type='int', required=False, default=8),
        binary_path=dict(type='str', required=False, default='orka-engine'),
        network_interface=dict(type='str', required=False)
    ),
        supports_check_mode=True
    )

    name = module.params['name']
    binary_path = module.params['binary_path']
    detached = module.params['detached']
    cpu = module.params['cpu']
    memory = module.params['memory']
    network_interface = module.params['network_interface']
    image = module.params['image']
    result = dict(
        changed=False,
        name='',
        command='',
    )

    def exit_with_result(changed, message):
        result['changed'] = changed
        result['name'] = name
        result['message'] = message
        module.exit_json(**result)

    vm = get_vm_info(module, name, binary_path, result)
    if vm:
        exit_with_result(False, f"VM '{name}' already exists in state '{vm['state']}'")

    if module.check_mode:
        exit_with_result(True, f"Would create VM '{name}' (check mode)")

    cmd = [binary_path, 'vm', 'run', name, '--image', image]

    if detached:
        cmd.append('-d')
    if cpu is not None:
        cmd.extend(['--cpu', str(cpu)])
    if memory is not None:
        cmd.extend(['--memory', str(memory)])
    if network_interface:
        cmd.extend(['--net-interface', network_interface])

    result['command'] = ' '.join(cmd)

    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        result['changed'] = True
        result['name'] = name

        try:
            result['process_id'] = int(proc.stdout.strip())
        except ValueError:
            result['process_id'] = None
            result['raw_output'] = proc.stdout.strip()

        module.exit_json(**result)
    except subprocess.CalledProcessError as e:
        module.fail_json(
            msg=f"Failed to create VM: {e.stderr}",
            rc=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
            **result
        )

def main():
    run_module()

if __name__ == '__main__':
    main()
