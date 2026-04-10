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

""" Method """

import time

# from pylon.core.tools import log  # pylint: disable=E0611,E0401
from pylon.core.tools import web  # pylint: disable=E0611,E0401

from ..tools.rooms import make_room_names


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.method()
    def on_log_data(self, _, data):
        """ Process log data event """
        # log.info("Log data: %s", data)
        room_cache_size = self.descriptor.config.get("room_cache_size", 100)
        #
        if "records" not in data:
            return
        #
        sio_rooms = {}
        #
        for record in data["records"]:
            rooms = make_room_names(record["labels"])
            #
            for room in rooms:
                self.room_timestamp[room] = time.time()
                #
                if room not in sio_rooms:
                    sio_rooms[room] = []
                #
                if room not in self.room_cache:
                    self.room_cache[room] = []
                #
                sio_rooms[room].append(record)
                self.room_cache[room].append(record)
                #
                while len(self.room_cache[room]) > room_cache_size:
                    self.room_cache[room].pop(0)
            #
        #
        # Emit to WebSocket for real-time UI streaming
        for room, records in sio_rooms.items():
            # log.info("--> Room: %s = %s", room, len(records))
            #
            self.context.sio.emit(
                event="log_data",
                data=records,
                room=room,
            )
        #
        # Export to OTEL Collector for durable storage/routing
        if self.otel_bridge and self.otel_bridge.enabled:
            self.otel_bridge.emit_batch(data["records"])
