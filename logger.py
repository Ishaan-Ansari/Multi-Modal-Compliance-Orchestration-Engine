import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(app_name: str, log_dir: str = 'logs'):
    """Sets up logger for the app"""
    logger = logging.getLogger(app_name)
    logger.setLevel(
        logging.DEBUG
    )   # Set the logging level (DEBUG, INFO, ERROR, CRITICAL)

    # log format including app_name
    formatter = logging.Formatter(
        f'%(asctime)s - {app_name} - %(name)s - %(levelname)s - %(message)s'
    )

    # create a log directory if it does not exist
    os.makedirs(os.path.join(os.getcwd(), log_dir), exist_ok=True)

    # File handler (with rotation)
    file_handler = RotatingFileHandler(
        f"{os.path.join(os.getcwd(), log_dir)}/{app_name}.log",
        maxBytes=10*1024*1024,
        backupCount=5,  # 10 MB per file, 5 backups
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

loggerNodes = setup_logger('Nodes')