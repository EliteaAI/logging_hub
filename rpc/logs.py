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

""" RPC """

# from pylon.core.tools import log  # pylint: disable=E0611,E0401
from pylon.core.tools import web  # pylint: disable=E0611,E0401

from ..tools.rooms import make_room_names


class RPC:  # pylint: disable=E1101,R0903
    """
        RPC Resource

        self is pointing to current Module instance

        Note: web.rpc decorator must be the last decorator (at top)
    """


    @web.rpc()
    def fetch_logs(self, labels):
        """ RPC handler """
        rooms = make_room_names(labels)
        result = []
        #
        for room in rooms:
            if room in self.room_cache:
                result.extend(self.room_cache[room])
        #
        return result
