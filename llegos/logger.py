import logging
import os

LOG_LEVEL = logging.getLevelName(os.environ.get("LLEGOS_LOG_LEVEL", "INFO"))

logger = logging.getLogger("llegos")
logger.setLevel(LOG_LEVEL)

getLogger = logger.getChild
