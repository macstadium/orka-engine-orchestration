#!/usr/bin/python3
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: plan_deployment
short_description: Plan VM deployments across multiple hosts based on capacity
version_added: "1.0"
description:
    - This module creates an optimal deployment plan for distributing VMs across hosts.
    - It takes into account current VM counts on each host and respects maximum capacity limits.
    - The output is a deployment plan that specifies how many VMs to deploy on each host.
    - The module fails if there is not enough capacity to deploy the requested number of VMs.

options:
    hosts_capacity:
        description:
            - List of dictionaries containing host capacity information.
            - Each dictionary must have 'hostname' and 'vms' keys.
        required: true
        type: list
        elements: dict
    total_vms_to_deploy:
        description:
            - The total number of VMs to deploy across all hosts.
        required: true
        type: int
    max_vms_per_host:
        description:
            - Maximum number of VMs allowed to run on each host.
        required: false
        default: 2
        type: int
    strategy:
        description:
            - The strategy to use when distributing VMs across hosts.
            - 'balanced' tries to distribute VMs evenly across hosts.
            - 'fill' fills each host to capacity before moving to the next.
        required: false
        default: 'fill'
        choices: ['balanced', 'fill']
        type: str

author:
    - Ivan Spasov (@ispasov)
"""

EXAMPLES = r"""
- name: Create a deployment plan for 5 VMs
  plan_deployment:
    hosts_capacity:
      - hostname: "host1.example.com"
        vms:
          - name: "vm1"
            state: "running"
          - name: "vm2"
            state: "stopped"
      - hostname: "host2.example.com"
        vms: []
      - hostname: "host3.example.com"
        vms:
          - name: "vm3"
            state: "running"
          - name: "vm4"
            state: "running"
    total_vms_to_deploy: 5
  register: deployment_plan

- name: Create a deployment plan with balanced strategy
  plan_deployment:
    hosts_capacity:
      - hostname: "host1.example.com"
        vms:
          - name: "vm1"
            state: "running"
      - hostname: "host2.example.com"
        vms: []
    total_vms_to_deploy: 10
    max_vms_per_host: 4
    strategy: 'balanced'
  register: deployment_plan
"""

RETURN = r"""
deployment_plan:
    description: Dictionary mapping host names to the number of VMs to deploy on each
    type: dict
    returned: success
    sample: {"host1.example.com": 2, "host2.example.com": 1, "host3.example.com": 2}
hosts_count:
    description: Number of hosts that will receive VMs
    type: int
    returned: success
    sample: 3
total_capacity:
    description: Total available capacity across all hosts
    type: int
    returned: success
    sample: 8
total_vms:
    description: Total number of VMs that will be deployed
    type: int
    returned: success
    sample: 5
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            hosts_capacity=dict(type="list", elements="dict", required=True),
            total_vms_to_deploy=dict(type="int", required=True),
            max_vms_per_host=dict(type="int", required=False, default=2),
            strategy=dict(
                type="str", required=False, default="fill", choices=["balanced", "fill"]
            ),
        ),
        supports_check_mode=True,
    )

    hosts_capacity = module.params["hosts_capacity"]
    total_vms_to_deploy = module.params["total_vms_to_deploy"]
    max_vms_per_host = module.params["max_vms_per_host"]
    strategy = module.params["strategy"]

    for host_info in hosts_capacity:
        if "hostname" not in host_info:
            module.fail_json(
                msg="Each host in hosts_capacity must have a 'hostname' key"
            )
        if "vms" not in host_info:
            module.fail_json(msg="Each host in hosts_capacity must have a 'vms' key")

    hosts_with_capacity = []
    for host_info in hosts_capacity:
        hostname = host_info["hostname"]
        vms = host_info["vms"] if host_info["vms"] is not None else []
        running_vms = sum(1 for vm in vms if vm.get("state") == "running")

        available_capacity = max_vms_per_host - running_vms
        if available_capacity > 0:
            hosts_with_capacity.append(
                {
                    "hostname": hostname,
                    "available_capacity": available_capacity,
                    "running_vms": running_vms,
                }
            )

    if strategy == "balanced":
        hosts_with_capacity.sort(key=lambda h: h["available_capacity"], reverse=True)
    elif strategy == "fill":
        hosts_with_capacity.sort(key=lambda h: h["running_vms"], reverse=True)

    total_available_capacity = sum(h["available_capacity"] for h in hosts_with_capacity)

    if total_available_capacity < total_vms_to_deploy:
        module.fail_json(
            msg=f"Not enough capacity to deploy {total_vms_to_deploy} VMs. "
            f"Only {total_available_capacity} slots available."
        )

    deployment_plan = {}
    remaining_vms = total_vms_to_deploy

    for host in hosts_with_capacity:
        hostname = host["hostname"]
        capacity = host["available_capacity"]

        to_deploy = min(capacity, remaining_vms)

        if to_deploy > 0:
            deployment_plan[hostname] = to_deploy
            remaining_vms -= to_deploy

        if remaining_vms <= 0:
            break

    result = {
        "changed": False,
        "deployment_plan": deployment_plan,
        "total_vms": total_vms_to_deploy,
        "total_capacity": total_available_capacity,
        "hosts_count": len(deployment_plan),
    }

    module.exit_json(**result)


if __name__ == "__main__":
    main()
