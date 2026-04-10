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

""" SIO """

# from pylon.core.tools import log  # pylint: disable=E0611,E0401
from pylon.core.tools import web  # pylint: disable=E0611,E0401

from tools import auth  # pylint: disable=E0401

from ..tools.rooms import make_room_names


class SIO:  # pylint: disable=E1101,R0903
    """
        SIO Resource

        self is pointing to current Module instance

        web.sio decorator takes one argument: event name
        Note: web.sio decorator must be the last decorator (at top)

        SIO resources use sio_check auth decorator
        auth.decorators.sio_check takes the following arguments:
        - permissions
        - scope_id=1
    """


    @web.sio("task_logs_subscribe")
    @auth.decorators.sio_check([])
    def task_logs_subscribe(self, sid, data):
        """ Event handler """
        # log.info("task_logs_subscribe: [%s] %s", sid, data)
        rooms = make_room_names(data)
        #
        for room in rooms:
            self.context.sio.enter_room(sid, room)
            #
            if room in self.room_cache:
                self.context.sio.emit(
                    event="log_data",
                    data=self.room_cache[room],
                    room=sid,
                )

    @web.sio("task_logs_unsubscribe")
    @auth.decorators.sio_check([])
    def task_logs_unsubscribe(self, sid, data):
        """ Event handler """
        # log.info("task_logs_unsubscribe: [%s] %s", sid, data)
        rooms = make_room_names(data)
        #
        for room in rooms:
            self.context.sio.leave_room(sid, room)
