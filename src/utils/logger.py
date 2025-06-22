"""
日志配置
"""
import sys
from loguru import logger
from pathlib import Path

def setup_logger(log_level: str = "INFO", log_file: str = "mediabot.log"):
    """配置日志系统"""
    
    # 移除默认处理器
    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # 文件输出
    log_path = Path("logs") / log_file
    log_path.parent.mkdir(exist_ok=True)
    
    logger.add(
        str(log_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    return logger

# 创建全局logger实例
log = setup_logger() 