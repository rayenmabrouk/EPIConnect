"""One-line JSON log records on stdout, the format CloudWatch Logs ingests best.

Every record becomes a single JSON object, so CloudWatch Logs Insights can
query fields directly and metric filters can match on e.g. {$.event = ...}.
"""
import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    RESERVED = set(vars(logging.makeLogRecord({}))) | {'message', 'asctime', 'request', 'server_time'}

    def format(self, record):
        payload = {
            'time': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in self.RESERVED and not key.startswith('_'):
                payload[key] = value
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)
