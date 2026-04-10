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

# from pylon.core.tools import log  # pylint: disable=E0611,E0401
from pylon.core.tools import web  # pylint: disable=E0611,E0401


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.method()
    def get_event_node_config(self):
        """ Get config for EventNode """
        local_config = self.descriptor.config.get("event_node", None)
        #
        if local_config is not None and "type" not in local_config:
            local_config["type"] = "RedisEventNode"
        #
        candidates = []
        candidates.append(local_config)
        #
        module_manager = self.context.module_manager
        #
        for module_name in ["worker_client"]:
            if module_name in module_manager.descriptors:
                cfg_descriptor = module_manager.descriptors[module_name]
                candidates.append(cfg_descriptor.config.get("event_node", None))
        #
        for candidate_config in candidates:
            if candidate_config is None or not isinstance(candidate_config, dict):
                continue
            #
            if candidate_config.get("type", "MockEventNode") == "MockEventNode":
                continue
            #
            result = candidate_config.copy()
            return result
        #
        return {
            "type": "MockEventNode",
        }
