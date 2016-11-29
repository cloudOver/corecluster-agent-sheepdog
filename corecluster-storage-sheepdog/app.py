MODULE = {
    'agents': [
        {'type': 'image', 'module': 'corecluster-storage-sheepdog.agents.image_sheepdog', 'count': 4},
        {'type': 'node', 'module': 'corecluster-storage-sheepdog.agents.node_sheepdog', 'count': 4},
        {'type': 'storage', 'module': 'corecluster-storage-sheepdog.agents.storage_sheepdog', 'count': 4},
    ],
    'drivers': {
        'CORE_DRIVER': 'corecluster-storage-sheepdog.drivers.core_sheepdog',
        'NODE_DRIVER': 'corecluster-storage-sheepdog.drivers.node_sheepdog',
    },
}
