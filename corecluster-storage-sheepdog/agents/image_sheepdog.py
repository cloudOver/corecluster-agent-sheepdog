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


import base64
import os
import subprocess
import urllib2
from corecluster.agents.base_agent import BaseAgent
from corecluster.cache.data_chunk import DataChunk
from corecluster.models.core import Device
from corecluster.exceptions.agent import *
from corenetwork.utils.logger import log
from corenetwork.utils import system


class AgentThread(BaseAgent):
    task_type = 'image'
    supported_actions = ['create', 'upload_url', 'upload_data', 'delete', 'duplicate', 'attach', 'detach']
    lock_on_fail = ['create', 'upload_url', 'upload_data', 'delete', 'duplicate']

    def task_failed(self, task, exception):
        if task.action in self.lock_on_fail:
            image = task.get_obj('Image')
            image.set_state('failed')
            image.save()

        super(AgentThread, self).task_failed(task, exception)


    def create(self, task):
        image = task.get_obj('Image')
        system.call('dog vdi create %s %d' % (image.libvirt_name, image.size), shell=True)

        image.set_state('ok')
        image.save()


    def upload_url(self, task):
        '''
        Download datq from url and put its contents into given image. Operation.data
        should contains:
        - action
        - url
        - size
        '''
        image = task.get_obj('Image')
        if image.attached_to is not None:
            raise TaskError('image_attached')

        image.set_state('downloading')
        image.save()

        try:
            remote = urllib2.urlopen(task.get_prop('url'))
        except Exception as e:
            raise TaskError('url_not_found', exception=e)

        # Create temporary object
        system.call('dog vdi create %s_tmp %s' % (image.libvirt_name, task.get_prop('size')), shell=True)
        bytes = 0

        while bytes < int(task.get_prop('size')):
            data = remote.read(1024*1024)
            if len(data) == 0:
                log(msg='End of data', context=task.logger_ctx, tags=('agent', 'image', 'info'))
                break
            try:
                p = subprocess.Popen(['dog', 'vdi', 'write', image.libvirt_name + '_tmp', str(bytes)], stdin=subprocess.PIPE)
                p.stdin.write(data)
                p.stdin.close()
                p.wait()
            except Exception as e:
                log(msg='Failed to finish download at %d bytes' % bytes, exception=e, context=task.logger_ctx, tags=('agent', 'image', 'error'))
                break

            bytes += len(data)
            image.set_prop('progress', float(bytes)/float(task.get_prop('size')))
            image.save()

        log(msg='Converting image %s to no-backend' %(image.libvirt_name), context=task.logger_ctx, tags=('agent', 'network', 'debug'))
        system.call('dog vdi delete %s' % image.libvirt_name, shell=True)
        r = system.call(['qemu-img', 'convert', '-f', image.format, 'sheepdog:%s_tmp' % image.libvirt_name, '-O', 'raw', 'sheepdog:%s' % image.libvirt_name])

        if r != 0:
            image.set_state('failed')
            image.save()
            return

        system.call('dog vdi delete %s_tmp' % image.libvirt_name, shell=True)

        image.size = int(task.get_prop('size'))
        image.set_state('ok')
        image.save()

        remote.close()


    def upload_data(self, task):
        '''
        Put file given in operation.data['filename'] into given image (operation.image)
        at offset. The file can extend existing image. Operation.data should contain:
        - action
        - offset
        - filename
        '''
        image = task.get_obj('Image')
        if image.image.attached_to is not None:
            raise TaskError('image_attached')

        image.set_state('downloading')
        image.save()

        data_chunk = DataChunk(cache_key=task.get_prop('chunk_id'))
        data = base64.b64decode(data_chunk.data)


        p = subprocess.Popen(['dog', 'vdi', 'write', str(bytes)], stdin=subprocess.PIPE)
        p.stdin.write(data)
        p.wait()

        os.remove(task.get_prop('filename'))

        image.size = int(task.get_prop('size'))
        image.set_state('ok')
        image.save()


    def delete(self, task):
        image = task.get_obj('Image')
        if image.attached_to is not None and not task.ignore_errors:
            raise TaskError('image_attached')

        for vm in image.vm_set.all():
            if not vm.in_state('closed') and not task.ignore_errors:
                raise TaskError('image_attached')

        system.call('dog vdi delete %s' % image.libvirt_name, shell=True)
        system.call('dog vdi delete %s_tmp' % image.libvirt_name, shell=True)

        image.set_state('deleted')
        image.save()


    def duplicate(self, task):
        image = task.get_obj('Image')
        if image.attached_to is not None:
            raise Exception('Image is attached to vm %s' % image.attached_to.vm.id)
        raise TaskError('not_implemented')


    def attach(self, task):
        image = task.get_obj('Image')
        vm = task.get_obj('VM')

        vm.node.check_online(task.ignore_errors)

        conn = vm.node.libvirt_conn()

        if image.attached_to is not None and not image.attached_to.in_state('closed'):
            raise TaskError('image_attached')

        if not vm.in_state('stopped'):
            raise TaskError('vm_not_stopped')

        if not image.in_state('ok'):
            raise TaskError('image_state')

        devices = [i.disk_dev for i in vm.image_set.all()]
        if 'device' in task.get_all_props().keys() and not int(task.get_prop('device')) in devices:
            disk_dev = int(task.get_prop('device'))
        else:
            disk_dev = 1
            while disk_dev in devices:
                disk_dev = disk_dev+1

        image.disk_dev = disk_dev
        image.attached_to = vm
        image.save()

        Device.create(image.id, vm, 'devices/image.xml', {'img': image, 'disk_dev': 'sd' + chr(ord('a')+disk_dev)})

        vm.libvirt_redefine()

        conn.close()


    def detach(self, task):
        image = task.get_obj('Image')
        vm = task.get_obj('VM')

        vm.node.check_online(task.ignore_errors)

        conn = vm.node.libvirt_conn()
        if not vm.in_states(['stopped', 'closed']) and not task.ignore_errors:
            raise TaskError('vm_not_stopped')

        image.attached_to = None
        image.save()

        for device in Device.objects.filter(object_id=image.id).all():
            device.delete()
        try:
            vm.libvirt_redefine()
        except:
            pass

        conn.close()
