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


import time
from corenetwork.utils import system
from corenetwork.utils.logger import log
from corenetwork.drivers.node_default import Driver as DefaultNodeDriver


class Driver(DefaultNodeDriver):
    def _sheepdog_startup(self):
        for i in xrange(30):
            r = system.call('dog node list', shell=True)
            if r == 0:
                break
            else:
                log(msg="sheepdog_startup: Restarting shepdog service", tags=('system', 'info'))
                system.call('service sheepdog restart', shell=True)
                time.sleep(i)

    def startup_node(self):
        """
        This method is called when node is started, by cc-node
        """
        super(Driver, self).startup_node()
        self._sheepdog_startup()
