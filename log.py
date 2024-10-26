from loguru import logger
import os
import time

log_dir = 'log/'
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

n = time.localtime(round(time.time()))
day = time.strftime("%Y-%m-%d", n)
logger.add(log_dir + f"{day}.log", rotation="500 MB")
