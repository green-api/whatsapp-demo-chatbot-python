import json
import logging
from datetime import datetime

import pytz


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_time = datetime.fromtimestamp(record.created, tz=pytz.utc).astimezone(
            pytz.timezone("Europe/Moscow")
        )
        formatted_time = log_time.strftime("%Y-%m-%d %H:%M:%S")

        log_record = {
            "time": formatted_time,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def init_logger(debug: bool) -> logging.Logger:
    logger = logging.getLogger("whatsapp_demo_bot")

    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(JsonFormatter())

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(stderr_handler)
    return logger
