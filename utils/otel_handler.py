"""
OTEL Log Bridge for logging_hub

Bridges log records from the EventNode to OpenTelemetry Log Exporter,
allowing logs to be routed through the OTEL Collector to various backends.

The bridge maintains the existing WebSocket streaming for real-time UI
while adding durable log export via OTLP.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from pylon.core.tools import log


# OTEL Log severity mapping
SEVERITY_MAP = {
    'DEBUG': 5,
    'INFO': 9,
    'WARNING': 13,
    'WARN': 13,
    'ERROR': 17,
    'CRITICAL': 21,
    'FATAL': 21,
}


class OTELLogBridge:
    """
    Bridge logging_hub events to OTEL LogRecords.

    This class converts log data from the EventNode format to OTEL LogRecords
    and exports them via OTLP to the Collector.
    """

    def __init__(
        self,
        endpoint: str = "http://otel-collector:4317",
        service_name: str = "pylon-logging-hub",
        insecure: bool = True
    ):
        """
        Initialize the OTEL Log Bridge.

        Args:
            endpoint: OTLP gRPC endpoint (default: otel-collector:4317)
            service_name: Service name for the resource
            insecure: Use insecure connection (no TLS)
        """
        self.endpoint = endpoint
        self.service_name = service_name
        self.insecure = insecure
        self._initialized = False
        self._logger = None
        self._logger_provider = None

    def init(self) -> bool:
        """
        Initialize the OTEL components.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            from opentelemetry.sdk.resources import Resource, SERVICE_NAME
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

            # Create resource
            resource = Resource.create({
                SERVICE_NAME: self.service_name,
            })

            # Create logger provider
            self._logger_provider = LoggerProvider(resource=resource)

            # Create OTLP exporter
            exporter = OTLPLogExporter(
                endpoint=self.endpoint,
                insecure=self.insecure,
            )

            # Add batch processor
            self._logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(exporter)
            )

            # Get logger
            self._logger = self._logger_provider.get_logger(
                "logging_hub",
                version="1.0.0"
            )

            self._initialized = True
            log.info(f"OTEL Log Bridge initialized - exporting to {self.endpoint}")
            return True

        except ImportError as e:
            log.warning(f"OTEL Log Bridge init failed - missing dependency: {e}")
            return False
        except Exception as e:
            log.warning(f"OTEL Log Bridge init failed: {e}")
            return False

    def _detect_source_service(self, labels: Dict[str, Any], message: str) -> str:
        """
        Detect the source service from log labels or message content.

        Args:
            labels: Log labels dict
            message: Log message

        Returns:
            Service name string (e.g., 'pylon-main', 'pylon-indexer')
        """
        import re

        # 1. Check explicit service label
        if labels.get('service'):
            return labels['service']
        if labels.get('service_name'):
            return labels['service_name']

        # 2. Extract service from log message format [service=pylon-xxx]
        # This is added by our trace_logging instrumentation
        service_match = re.search(r'\[service=([^\]]+)\]', message)
        if service_match:
            return service_match.group(1)

        # 3. Check logger name for service hints
        logger = labels.get('logger', '')

        # Map known logger patterns to services
        logger_service_map = {
            'plugins.indexer_worker': 'pylon-indexer',
            'plugins.elitea_core': 'pylon-main',
            'plugins.auth_core': 'pylon-auth',
            'plugins.logging_hub': 'pylon-main',
            'plugins.tracing': 'pylon-main',
            'plugins.runtime': 'pylon-predicts',
            'plugins.configurations': 'pylon-main',
            'plugins.conversations': 'pylon-main',
            'plugins.toolkits': 'pylon-main',
            'plugins.applications': 'pylon-main',
            'plugins.datasources': 'pylon-main',
            'plugins.prompts': 'pylon-main',
            'plugins.projects': 'pylon-main',
            'plugins.secrets': 'pylon-main',
            'plugins.scheduling': 'pylon-main',
            'plugins.social': 'pylon-main',
            'plugins.theme': 'pylon-main',
            'elitea_sdk': 'pylon-indexer',
            'langchain': 'pylon-indexer',
            'litellm': 'pylon-predicts',
        }

        for pattern, service in logger_service_map.items():
            if pattern in logger:
                return service

        # 3. Check hostname/container labels
        hostname = labels.get('hostname', '').lower()
        container = labels.get('container_name', '').lower()

        for name in [hostname, container]:
            if 'indexer' in name:
                return 'pylon-indexer'
            if 'main' in name:
                return 'pylon-main'
            if 'auth' in name:
                return 'pylon-auth'
            if 'predict' in name:
                return 'pylon-predicts'

        # 4. Check message content for hints
        message_lower = message.lower()
        if 'indexer' in message_lower or 'worker' in message_lower:
            return 'pylon-indexer'
        if 'auth' in message_lower:
            return 'pylon-auth'

        # 5. Default fallback
        return self.service_name

    def emit(self, log_data: Dict[str, Any]) -> None:
        """
        Convert logging_hub event to OTEL LogRecord and emit.

        Args:
            log_data: Log record from EventNode with keys:
                - timestamp: Log timestamp
                - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                - message: Log message
                - labels: Dict with task_id, stream_id, etc.
        """
        if not self._initialized or not self._logger:
            return

        try:
            from opentelemetry._logs import SeverityNumber
            import re

            # Parse timestamp from log_data
            # EventNode logs have 'time' (float timestamp) and 'line' (message)
            raw_time = log_data.get('time')
            if raw_time:
                timestamp_ns = int(raw_time * 1e9)
            else:
                timestamp_ns = int(datetime.now().timestamp() * 1e9)

            # Get message - EventNode uses 'line' key
            message = log_data.get('line', log_data.get('message', ''))

            # Get labels
            labels = log_data.get('labels', {})

            # Get severity from labels
            level = labels.get('level', 'INFO').upper()
            severity_number = SEVERITY_MAP.get(level, 9)

            # Detect source service from labels
            source_service = self._detect_source_service(labels, message)

            # Build attributes
            # NOTE: Don't use 'service.name' here - it gets shadowed by Resource SERVICE_NAME
            # Use 'source_service' and other names which won't conflict
            attributes = {
                'telemetry.data_type': 'logs',
                'log.level': level,
                # Primary attribute for service filtering (won't conflict with Resource)
                'source_service': source_service,
                # Additional names that may be indexed by different backends
                'log.io.service': source_service,
                'pylon.service': source_service,
                # log.source is commonly used for filtering in observability tools
                'log.source': source_service,
            }

            # Add labels as attributes
            if labels.get('tasknode_task'):
                attributes['task.id'] = labels['tasknode_task']
            if labels.get('stream_id'):
                attributes['stream.id'] = labels['stream_id']
            if labels.get('project_id'):
                attributes['project.id'] = str(labels['project_id'])
            if labels.get('logger'):
                attributes['logger.name'] = labels['logger']
            if labels.get('level'):
                attributes['log.level'] = labels['level']

            # Add hostname/container info if available (these help with service detection)
            hostname = labels.get('host.name', labels.get('hostname', ''))
            container = labels.get('container_name', labels.get('container.name', ''))
            if hostname:
                attributes['host.name'] = hostname
            if container:
                attributes['container.name'] = container

            # Use container name as additional source hint if available
            if container and not source_service.startswith('pylon-'):
                # Container name often includes service info (e.g., centry-pylon_indexer-1)
                if 'indexer' in container.lower():
                    attributes['source_service'] = 'pylon-indexer'
                elif 'main' in container.lower():
                    attributes['source_service'] = 'pylon-main'
                elif 'auth' in container.lower():
                    attributes['source_service'] = 'pylon-auth'
                elif 'predict' in container.lower():
                    attributes['source_service'] = 'pylon-predicts'

            # Extract trace context from message (format: [trace_id=xxx span_id=yyy])
            trace_id = None
            span_id = None

            # Try to extract from message
            trace_match = re.search(r'trace_id=([a-fA-F0-9]+)', message)
            span_match = re.search(r'span_id=([a-fA-F0-9]+)', message)
            if trace_match:
                trace_id = trace_match.group(1)
            if span_match:
                span_id = span_match.group(1)

            # Override with labels if present
            if labels.get('trace_id'):
                trace_id = labels['trace_id']
            if labels.get('span_id'):
                span_id = labels['span_id']

            # Add trace context to attributes (for backends that use attributes)
            if trace_id and trace_id != '0' * 32:
                attributes['trace_id'] = trace_id
            if span_id and span_id != '0' * 16:
                attributes['span_id'] = span_id

            # Build proper OTEL trace context for log-trace correlation
            trace_context = None
            if trace_id and trace_id != '0' * 32:
                try:
                    from opentelemetry.trace import SpanContext, TraceFlags
                    from opentelemetry.trace import set_span_in_context, NonRecordingSpan
                    from opentelemetry.context import Context

                    # Parse trace_id and span_id as integers
                    trace_id_int = int(trace_id, 16)
                    span_id_int = int(span_id, 16) if span_id and span_id != '0' * 16 else 0

                    # Create SpanContext with the extracted trace context
                    span_context = SpanContext(
                        trace_id=trace_id_int,
                        span_id=span_id_int,
                        is_remote=True,
                        trace_flags=TraceFlags(TraceFlags.SAMPLED),
                    )

                    # Create a non-recording span with this context
                    span = NonRecordingSpan(span_context)

                    # Set the span in a new context
                    trace_context = set_span_in_context(span)
                except Exception:
                    # If trace context creation fails, continue without it
                    pass

            # Emit the log record with trace context for proper correlation
            emit_kwargs = {
                'timestamp': timestamp_ns,
                'observed_timestamp': int(datetime.now().timestamp() * 1e9),
                'body': message,
                'severity_number': SeverityNumber(severity_number),
                'severity_text': level,
                'attributes': attributes,
            }

            # Add trace context if available
            if trace_context:
                emit_kwargs['context'] = trace_context

            self._logger.emit(**emit_kwargs)

        except Exception as e:
            # Don't log errors during log processing to avoid loops
            pass

    def emit_batch(self, records: list) -> None:
        """
        Emit multiple log records.

        Args:
            records: List of log records from EventNode
        """
        for record in records:
            self.emit(record)

    def shutdown(self) -> None:
        """Shutdown the logger provider and flush pending logs."""
        if self._initialized and self._logger_provider:
            try:
                self._logger_provider.force_flush()
                self._logger_provider.shutdown()
                log.info("OTEL Log Bridge shutdown complete")
            except Exception as e:
                log.warning(f"OTEL Log Bridge shutdown error: {e}")

    @property
    def enabled(self) -> bool:
        """Check if the bridge is initialized and enabled."""
        return self._initialized
