"""
Copyright (c) 2014 Maciej Nabozny
              2015 Marta Nabozny

This file is part of CloudOver project.

CloudOver is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
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
