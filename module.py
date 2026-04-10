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

""" Module """

import os

from pylon.core.tools import log  # pylint: disable=E0611,E0401
from pylon.core.tools import module  # pylint: disable=E0611,E0401

import arbiter  # pylint: disable=E0611,E0401

from .tools.housekeeper import RoomHousekeeper
from .utils.otel_handler import OTELLogBridge


class Module(module.ModuleModel):
    """ Pylon module """

    def __init__(self, context, descriptor):
        self.context = context
        self.descriptor = descriptor
        #
        self.event_node_config = None
        self.event_node = None
        #
        self.room_cache = {}
        self.room_timestamp = {}
        #
        # OTEL Log Bridge for exporting logs via OTLP
        self.otel_bridge = None

    def init(self):
        """ Init module """
        log.info("Initializing module")
        # Init
        self.descriptor.init_all()
        # EventNode
        self.event_node_config = self.get_event_node_config()
        self.event_node = arbiter.make_event_node(
            config=self.event_node_config,
        )
        self.event_node.start()
        self.event_node.subscribe("log_data", self.on_log_data)
        # RoomHousekeeper
        RoomHousekeeper(self).start()
        # OTEL Log Bridge (optional - enabled via config or env var)
        self._init_otel_bridge()

    def _init_otel_bridge(self):
        """Initialize OTEL Log Bridge if enabled."""
        # Check if OTEL export is enabled
        otel_config = self.descriptor.config.get('otel_export', {})
        otel_enabled = otel_config.get('enabled', False)

        # Environment variable override
        env_enabled = os.environ.get('LOGGING_HUB_OTEL_ENABLED', '').lower()
        if env_enabled == 'true':
            otel_enabled = True
        elif env_enabled == 'false':
            otel_enabled = False

        if not otel_enabled:
            log.info("OTEL Log Bridge is DISABLED (set otel_export.enabled: true in config)")
            return

        # Get OTEL endpoint from config or env
        endpoint = os.environ.get(
            'LOGGING_HUB_OTEL_ENDPOINT',
            otel_config.get('endpoint', 'http://otel-collector:4317')
        )
        service_name = otel_config.get('service_name', 'pylon-logging-hub')
        insecure = otel_config.get('insecure', True)

        # Initialize the bridge
        self.otel_bridge = OTELLogBridge(
            endpoint=endpoint,
            service_name=service_name,
            insecure=insecure,
        )

        if self.otel_bridge.init():
            log.info(f"OTEL Log Bridge enabled - exporting logs to {endpoint}")
        else:
            log.warning("OTEL Log Bridge initialization failed - logs will not be exported to OTEL")
            self.otel_bridge = None

    def deinit(self):
        """ De-init module """
        log.info("De-initializing module")
        # OTEL Log Bridge
        if self.otel_bridge:
            self.otel_bridge.shutdown()
        # EventNode
        self.event_node.unsubscribe("log_data", self.on_log_data)
        self.event_node.stop()
        # De-init
        self.descriptor.deinit_all()
