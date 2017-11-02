"""
Copyright (C) 2014-2017 cloudover.io ltd.
This file is part of the CloudOver.org project

Licensee holding a valid commercial license for this software may
use it in accordance with the terms of the license agreement
between cloudover.io ltd. and the licensee.

Alternatively you may use this software under following terms of
GNU Affero GPL v3 license:

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version. For details contact
with the cloudover.io company: https://cloudover.io/


This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.


You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import libvirt
import time

from corecluster.models.core.vm import VM
from corecluster.agents.base_agent import BaseAgent
from corecluster.exceptions.agent import *
from corenetwork.utils.logger import log
from corenetwork.utils import system, config


class AgentThread(BaseAgent):
    task_type = 'node'
    supported_actions = ['load_image', 'delete', 'save_image', 'mount', 'umount', 'create_images_pool', 'check', 'suspend', 'wake_up']


    def load_image(self, task):
        image = task.get_obj('Image')
        vm = task.get_obj('VM')

        vm.node.check_online(task.ignore_errors)

        if image.state != 'ok':
            raise TaskNotReady('image_wrong_state')

        rc = None
        if not task.ignore_errors:
            rc = 0

        system.call('dog vdi snapshot -s snap_%s %s' % (vm.id, image.libvirt_name), shell=True, retcode=rc)
        system.call('dog vdi clone -s snap_%s %s %s' % (vm.id, image.libvirt_name, vm.id), shell=True, retcode=rc)
        system.call('dog vdi delete -s snap_%s %s' % (vm.id, image.libvirt_name), shell=True, retcode=rc)


    def delete(self, task):
        '''
        Delete base image from node
        '''
        vm = task.get_obj('VM')

        vm.node.check_online(task.ignore_errors)

        if vm.state not in ['stopped', 'closed', 'closing'] and not task.ignore_errors:
            raise TaskNotReady('vm_not_stopped')

        system.call('dog vdi delete %s' % (vm.id), shell=True)


    def save_image(self, task):
        vm = task.get_obj('VM')

        vm.node.check_online(task.ignore_errors)

        image = task.get_obj('Image')

        if not vm.in_state('stopped'):
            raise TaskNotReady('vm_not_stopped')

        vm.set_state('saving')
        vm.save()

        # Save snapshot from VM (based on vm.base_image) to clone of image (operation.image)
        rc = None
        if not task.ignore_errors:
            rc = 0
        system.call('dog vdi snapshot -s snap_%s %s' % (vm.id, vm.id), shell=True, retcode=rc)
        system.call('dog vdi clone -s snap_%s %s %s' % (vm.id, vm.id, image.libvirt_name), shell=True, retcode=rc)
        system.call('dog vdi delete -s snap_%s %s' % (vm.id, vm.id), shell=True, retcode=rc)

        vm.set_state('stopped')
        vm.save()

        image.set_state('ok')
        image.save()


    def mount(self, task):
        pass


    def umount(self, task):
        node = task.get_obj('Node')
        node.state = 'offline'
        node.save()


    def create_images_pool(self, operation):
        pass


    def check(self, task):
        node = task.get_obj('Node')
        conn = node.libvirt_conn()

        for vm in node.vm_set.filter(state__in=['running', 'starting']):
            try:
                libvirt_vm = conn.lookupByName(vm.libvirt_name)
            except Exception as e:
                vm.set_state('stopped')
                vm.save()
                log(msg='Failed to find VM %s at node %s' % (vm.id, vm.node.address),
                    exception=e,
                    tags=('agent', 'node', 'info'),
                    context=task.logger_ctx)

            if libvirt_vm.state() == libvirt.VIR_DOMAIN_RUNNING:
                vm.set_state('running')
                vm.save()
            else:
                vm.set_state('stopped')
                vm.save()
        conn.close()

        node.state = 'ok'
        node.save()


    def suspend(self, task):
        """
        Suspend node to RAM for defined in config seconds. After this time + NODE_WAKEUP_TIME
        node is suspended again, unles it's state is not wake up. Available only
        in admin site or through plugins.
        """
        node = task.get_obj('Node')

        if VM.objects.filter(node=node).exclude(state='closed').count() > 0:
            task.comment = "Node is in use. Aborting suspend"
            task.save()
            return

        node.set_state('suspend')
        node.save()

        log(msg="Suspending node %s" % node.address, tags=('agent', 'node', 'info'))
        system.Popen(['ping', '-c', '1', node.address])

        arp = open('/proc/net/arp', 'r').readlines()
        for line in arp:
            fields = line.split()
            if fields[0] == node.address:
                node.set_prop('mac', fields[3])

        node.save()

        conn = node.libvirt_conn()
        conn.suspendForDuration(libvirt.VIR_NODE_SUSPEND_TARGET_MEM, config.get('core', 'NODE_SUSPEND_DURATION'))
        conn.close()


    def wake_up(self, task):
        node = task.get_obj('Node')
        if node.mac != '':
            system.call(['wakeonlan', node.mac])
            if node.in_state('suspend'):
                time.sleep(config.get('core', 'NODE_WAKEUP_TIME'))
                node.start()
        else:
            raise TaskError('Cannot find node\'s MAC')
