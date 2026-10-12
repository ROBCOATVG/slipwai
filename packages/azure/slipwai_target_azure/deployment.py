"""Deployment choices owned by this target, separate from bootstrap/service stack phases."""
from __future__ import annotations


def choices(stacks: dict, scripts: dict) -> dict:
    liner = {phase: {path: path for path in paths} for phase, paths in stacks.items()}
    skiff = {phase: dict(files) for phase, files in liner.items()}
    skiff['service'].pop('service/staging.tfvars')
    skiff['service']['service/production.tfvars'] = 'skiff/production.tfvars'
    database = 'PostgreSQL Flexible Server on the existing firewall and TLS policy'
    return {
        'skiff': {
            'compute': 'Azure Container Apps Consumption with HTTP scale to zero',
            'database': database,
            'stacks': skiff,
            'scripts': scripts,
            'environments': ('production',),
            'guidance': 'One production environment, 0.25 vCPU and 0.5 GiB per replica, with a zero replica '
                'floor and HTTP ingress to wake it. The database keeps its managed burstable tier and '
                'existing firewall/TLS policy; it does not scale to zero. A first request can cold-start. '
                'See https://learn.microsoft.com/azure/container-apps/scale-app.',
            'transition': 'Moving to a liner retains the production database and resource addresses. '
                'Keep the existing state and take a database backup before changing scaling. Review the '
                'prepared module against that state; import existing resources if a new state is used, '
                'and refuse a plan that replaces the database. Validate the new application before '
                'switching its public address; do not delete the old stack as part of preparation.',
        },
        'liner': {
            'compute': 'Azure Container Apps Consumption with retained production replicas',
            'database': database,
            'stacks': liner,
            'scripts': scripts,
            'environments': ('staging', 'production'),
            'guidance': 'Staging proves each immutable image before production receives it. Production '
                'keeps its configured replica floor and previous revision for rollback.',
            'transition': 'Use the existing production state and database when expanding a skiff. '
                'Provision staging separately; never seed it by moving or deleting production data.',
        },
    }
