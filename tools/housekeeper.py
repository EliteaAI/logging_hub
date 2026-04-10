#!/usr/bin/python3
# coding=utf-8

#   Copyright 2026 EPAM Systems
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
    Room maid
"""

import time
import threading

from pylon.core.tools import log  # pylint: disable=E0611,E0401


class RoomHousekeeper(threading.Thread):  # pylint: disable=R0903
    """ Perform cleanup """

    def __init__(self, module):
        super().__init__(daemon=True)
        #
        self.module = module
        self.stop_event = threading.Event()
        #
        self.housekeeping_interval = self.module.descriptor.config.get(
            "room_housekeeping_interval", 3600,
        )

    def run(self):
        """ Run housekeeper thread """
        while not self.stop_event.is_set():
            time.sleep(self.housekeeping_interval)
            #
            try:
                self._clean_rooms()
            except:  # pylint: disable=W0702
                pass

    def _clean_rooms(self):
        now = time.time()
        for room_name, room_timestamp in list(self.module.room_timestamp.items()):
            if abs(now - room_timestamp) >= self.module.descriptor.config.get(
                    "room_ttl", 86400,
            ):
                log.info("Room TTL expired: %s", room_name)
                #
                self.module.room_cache.pop(room_name, None)
                self.module.room_timestamp.pop(room_name, None)
