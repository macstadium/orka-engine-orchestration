#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: orka_vm_delete
short_description: Delete a VM using Orka Engine
description:
    - Delete a virtual machine using orka-engine
    - Stops the VM first if it's running
    - Executes 'orka-engine vm delete' command with provided parameters
    - Idempotent: succeeds even if the VM doesn't exist
options:
    name:
        description: Name of the VM to delete
        required: true
        type: str
    binary_path:
        description: Path to the orka-engine binary
        required: false
        type: str
        default: "orka-engine"
author:
    - "Ivan Spasov (@ispasov)"
'''

EXAMPLES = r'''
- name: Delete a VM
  orka_vm_delete:
    name: test_vm

- name: Delete a VM with custom binary path
  orka_vm_delete:
    name: test_vm
    binary_path: /usr/local/bin/orka-engine
'''

RETURN = r'''
name:
    description: Name of the VM that was deleted
    type: str
    returned: always
'''

import json
import subprocess
import time
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orka_utils import get_vm_info

def stop_vm(module, name, binary_path, result):
    stop_cmd = [binary_path, 'vm', 'stop', name]
    result['command'] = ' '.join(stop_cmd)
    
    try:
        subprocess.run(stop_cmd, check=True, capture_output=True, text=True)
        
        max_attempts = 10
        for attempt in range(max_attempts):
            current_vm = get_vm_info(module, name, binary_path, result)
            
            if not current_vm or current_vm.get('state') != "running":
                break
                
            if attempt < max_attempts - 1:
                time.sleep(1)
        
    except subprocess.CalledProcessError as e:
        module.fail_json(
            msg=f"Failed to stop VM before deletion: {e.stderr}",
            rc=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
            **result
        )

def delete_vm(module, name, binary_path, result):
    delete_cmd = [binary_path, 'vm', 'delete', name]
    result['command'] = ' '.join(delete_cmd)
    
    try:
        proc = subprocess.run(delete_cmd, check=True, capture_output=True, text=True)

        if ("is running and could not be deleted" in proc.stdout.lower()):
            module.fail_json(
                msg=f"VM '{name}' is running and could not be deleted",
                stdout=proc.stdout,
                stderr=proc.stderr,
                **result
            )
            
        return True, f"VM '{name}' deleted successfully"
    except subprocess.CalledProcessError as e:
        if "could not be found" in e.stderr.lower():
            return False, f"VM '{name}' does not exist, nothing to delete"
        elif ("is running and could not be deleted" in e.stderr.lower()):
            module.fail_json(
                msg=f"VM '{name}' is running and could not be deleted",
                rc=e.returncode,
                stdout=e.stdout,
                stderr=e.stderr,
                **result
            )
        else:
            module.fail_json(
                msg=f"Failed to delete VM: {e.stderr}",
                rc=e.returncode,
                stdout=e.stdout,
                stderr=e.stderr,
                **result
            )

def run_module():
    module = AnsibleModule(
        argument_spec=dict(
        name=dict(type='str', required=True),
        binary_path=dict(type='str', required=False, default='orka-engine')
    ),
        supports_check_mode=True
    )

    name = module.params['name']
    binary_path = module.params['binary_path']

    result = dict(
        changed=False,
        name=name,
        command='',
    )

    def exit_with_result(changed, message):
        result['changed'] = changed
        result['name'] = name
        result['message'] = message
        module.exit_json(**result)
    
    existing_vm = get_vm_info(module, name, binary_path, result)
    if not existing_vm:
        exit_with_result(False, f"VM '{name}' does not exist, nothing to delete")
    
    vm_state = existing_vm.get('state')

    if module.check_mode:
        exit_with_result(True, f"Would delete VM '{name}' (check mode)")

    if vm_state == "running":
        stop_vm(module, name, binary_path, result)

    changed, message = delete_vm(module, name, binary_path, result)
    exit_with_result(changed, message)

def main():
    run_module()

if __name__ == '__main__':
    main()
