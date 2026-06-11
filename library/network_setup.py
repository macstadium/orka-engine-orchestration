#!/usr/bin/python3
# -*- coding: utf-8 -*-

import subprocess

from ansible.module_utils.basic import *
from ansible.module_utils._text import to_text

DOCUMENTATION = r"""
module: network_setup
short_description: Sets up a VLAN
description:
    - Configure a VLAN and network service
options:
    name:
        description:
            - VLAN name
        type: string
        required: true
    device:
        description:
            - The device used (en0, en1, etc...)
        type: string
        required: false
    tag:
        description:
            - The VLAN tag
        type: string
        required: false
    ip:
        description:
            - IP of the service
        type: str
        required: false
    mask:
        description:
            - Mask of the service
        type: str
        required: false
    router:
        description:
            - Router of the service
        type: str
        required: false
    state:
        description:
            - Add, delete, enable or disable the interface
        type: str
        choices: [ present, absent, enable, disable ]
        default: present
    force:
        description:
            - Apply the change regardless of current state
        type: bool
        default: false
author:
- Ivan Spasov (@ispasov)
- Spike Burton (@spikeburton)
"""

EXAMPLES = r"""
- name: Add a storage vlan
  network_setup:
    name: storage
    device: en0
    tag: 2339
    ip: 10.172.1.12
    mask: 255.255.254.0
    router: 10.172.1.11
- name: Remove a storage vlan
  network_setup:
    name: storage
    device: en0
    tag: 2339
    ip: 10.172.1.12
    mask: 255.255.254.0
    router: 10.172.1.11
    state: absent
- name: Force recreate a storage vlan
  network_setup:
    name: storage
    device: en0
    tag: 2339
    ip: 10.172.1.12
    mask: 255.255.254.0
    router: 10.172.1.11
    force: true
"""


class NetworkServiceModuleError(Exception):
    pass


class NetworkService(object):
    def __init__(self, module):
        self.module = module
        self.name = module.params['name']
        self.device = module.params['device']
        self.tag = module.params['tag']
        self.ip = module.params['ip']
        self.mask = module.params['mask']
        self.router = module.params['router']
        self.state = module.params['state']
        self.force = module.params['force']

    def execute_command(self, cmd):
        cmd = [to_text(item) for item in cmd]
        (rc, out, err) = self.module.run_command(cmd)
        if rc != 0:
            raise NetworkServiceModuleError(out + err)

        return out

    def vlan_exists(self):
        out = self.execute_command(['networksetup', '-listVlans'])

        return f'VLAN User Defined Name: {self.name}' in out.splitlines()

    def create(self):
        self.create_vlan()
        self.configure_service()
        self.configure_dns()

    def create_vlan(self):
        cmd = ['networksetup', '-createVLAN', self.name, self.device, self.tag]
        self.execute_command(cmd)

    def configure_service(self):
        cmd = ['networksetup', '-setmanual', f'{self.name} Configuration', self.ip, self.mask, self.router]
        self.execute_command(cmd)

    def configure_dns(self):
        cmd = ['networksetup', '-setdnsservers', f'{self.name} Configuration', '8.8.8.8', '1.1.1.1']
        self.execute_command(cmd)

    def vlan_changed(self):
        out = self.execute_command(['networksetup', '-listVlans'])
        vlan_lines = out.splitlines()
        vlan_name_index = vlan_lines.index(f'VLAN User Defined Name: {self.name}')
        vlan_device = vlan_lines[vlan_name_index + 1].replace('Parent Device:', '').strip()
        vlan_tag = vlan_lines[vlan_name_index + 3].replace('Tag:', '').strip()

        return vlan_device != self.device or vlan_tag != self.tag

    def service_changed(self):
        out = self.execute_command(['networksetup', '-getinfo', f'{self.name} Configuration'])
        service_lines = out.splitlines()
        service_ip = service_lines[1].replace('IP address:', '').strip()
        service_mask = service_lines[2].replace('Subnet mask:', '').strip()
        service_router = service_lines[3].replace('Router:', '').strip()

        return service_ip != self.ip or service_mask != self.mask or service_router != self.router

    def needs_update(self):
        return self.vlan_changed() or self.service_changed()

    def delete(self):
        cmd = ['networksetup', '-deleteVLAN', self.name, self.device, self.tag]
        self.execute_command(cmd)

    def service_exists(self):
        cmd = ['networksetup', '-listallnetworkservices']
        out = self.execute_command(cmd)

        for line in out.splitlines():
            service_name = line.lstrip('*').strip()
            if service_name == self.name:
                return True
        return False

    def service_enabled(self):
        cmd = ['networksetup', '-getnetworkserviceenabled', self.name]
        out = self.execute_command(cmd)
        return out.strip().lower() == 'enabled'

    def enable_service(self):
        cmd = ['networksetup', '-setnetworkserviceenabled', self.name, 'on']
        self.execute_command(cmd)

    def disable_service(self):
        cmd = ['networksetup', '-setnetworkserviceenabled', self.name, 'off']
        self.execute_command(cmd)

    def set_service_state(self):
        should_enable = self.state == 'enable'
        is_currently_enabled = self.service_enabled()

        if self.force or is_currently_enabled != should_enable:
            self.enable_service() if should_enable else self.disable_service()
            return True

        return False

    def run(self):
        changed = False

        if self.state == 'present':
            if not self.vlan_exists():
                self.create()
                changed = True
            elif self.force or self.needs_update():
                self.delete()
                self.create()
                changed = True

        elif self.state == 'absent' and self.vlan_exists():
            self.delete()
            changed = True

        elif self.service_exists() and self.state in ['enable', 'disable']:
            changed = self.set_service_state()

        return changed


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            device=dict(type='str'),
            tag=dict(type='str'),
            ip=dict(type='str'),
            mask=dict(type='str', default='manual'),
            router=dict(type='str'),
            state=dict(type='str', default='present', choices=['present', 'absent', 'enable', 'disable']),
            force=dict(type='bool', default=False),
        ),
        required_if=[
            ('state', 'present', ('device', 'tag', 'ip', 'mask', 'router')),
            ('state', 'absent', ('device', 'tag')),
        ],
        supports_check_mode=False,
    )

    network_service = NetworkService(module)
    try:
        changed = network_service.run()
    except Exception as e:
        module.fail_json(msg=str(e))

    module.exit_json(changed=changed)


if __name__ == '__main__':
    main()
