import os
import sys
from pathlib import Path
from loguru import logger

# Paths inside the container
# MovieRecs/src/utils/logger.py
# .parent = utils
# .parent.parent = src
# .parent.parent.parent = MovieRecs
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE_PATH = LOG_DIR / "service.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

config = {
    "handlers": [
        {
            "sink": sys.stdout,
            "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            "level": "INFO",
        },
        {
            "sink": str(LOG_FILE_PATH),
            "serialize": True,
            "rotation": "100 MB",
            "retention": "10 days",
            "level": "INFO",
        }
    ]
}

logger.configure(**config)
