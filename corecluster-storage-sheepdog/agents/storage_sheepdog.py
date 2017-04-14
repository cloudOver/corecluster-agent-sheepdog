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


import os
from corecluster.agents.base_agent import BaseAgent
from corenetwork.utils import system

class AgentThread(BaseAgent):
    task_type = 'storage'
    supported_actions = ['mount', 'umount']
    

    def mount(self, task):
        system.call('service sheepdog start', shell=True)

        storage = task.get_obj('Storage')
        storage.state = 'ok'
        storage.save()


    def umount(self, task):
        system.call('service sheepdog stop', shell=True)

        storage = task.get_obj('Storage')
        storage.state = 'locked'
        storage.save()
