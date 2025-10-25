"""
Logger with debug & info with file logging
"""
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Log directory
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Timezone IST
IST_OFFSET = timedelta(hours=5, minutes=30)
logging.Formatter.converter = lambda *args: (datetime.now(timezone(IST_OFFSET))).timetuple()
# Create formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s ")


# Create logger
logger = logging.getLogger("github_application_builder")
logger.setLevel(logging.DEBUG)

# Add handlers
debug_handler = logging.FileHandler(LOG_DIR / "debug.log")
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(formatter)

info_handler = logging.FileHandler(LOG_DIR / "info.log")
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger.addHandler(debug_handler)
logger.addHandler(info_handler)
logger.addHandler(console_handler)
