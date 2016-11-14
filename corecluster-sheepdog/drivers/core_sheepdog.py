"""
Copyright (c) 2015 Maciej Nabozny
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

from corenetwork.drivers.core_default import Driver as DefaultNodeDriver
from corenetwork.utils import system
from corenetwork.utils.logger import log
import time

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


    def startup_core(self):
        """
        This method is called when node is started, by cc-node
        """
        super(Driver, self).startup_core()
        self._sheepdog_startup()
