"""
Session 专用日志管理器
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from loguru import logger
import sys

class SessionLogger:
    """Session专用日志管理器"""
    
    _loggers: Dict[str, Any] = {}
    _handlers: Dict[str, tuple] = {}
    
    @classmethod
    def get_logger(cls, session_id: str) -> Any:
        """获取session专用logger"""
        if session_id not in cls._loggers:
            cls._create_session_logger(session_id)
        return cls._loggers[session_id]
    
    @classmethod
    def _create_session_logger(cls, session_id: str):
        """创建session专用logger"""
        # 创建session日志目录
        session_log_dir = Path("logs/sessions") / session_id
        session_log_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 日志文件路径
        log_file = session_log_dir / f"{session_id}_{timestamp}.log"
        
        # 创建新的logger实例，确保session_id正确绑定
        session_logger = logger.bind(session_id=session_id)
        
        # 添加控制台输出（带session标识）
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>[{extra[session_id]}]</cyan> | "
            "<level>{message}</level>"
        )
        
        # 移除可能的默认handler，避免重复输出
        if hasattr(session_logger, '_handlers'):
            try:
                session_logger.remove()
            except:
                pass
        
        console_handler = session_logger.add(
            sys.stdout,
            format=console_format,
            level="INFO",
            filter=lambda record: record["extra"].get("session_id") == session_id
        )
        
        # 添加文件输出
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "[{extra[session_id]}] | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        
        file_handler = session_logger.add(
            log_file,
            format=file_format,
            level="DEBUG",
            rotation="100 MB",
            retention="7 days",
            encoding="utf-8",
            filter=lambda record: record["extra"].get("session_id") == session_id
        )
        
        # 保存logger和handler引用
        cls._loggers[session_id] = session_logger
        cls._handlers[session_id] = (console_handler, file_handler)
        
        # 确保session_id在记录中
        session_logger.info(f"Session logger initialized: {log_file}")
    
    @classmethod
    def close_session_logger(cls, session_id: str):
        """关闭session logger"""
        if session_id in cls._loggers:
            try:
                # 记录关闭信息
                cls._loggers[session_id].info(f"Closing session logger for: {session_id}")
                
                # 移除handlers
                if session_id in cls._handlers:
                    console_handler, file_handler = cls._handlers[session_id]
                    try:
                        logger.remove(console_handler)
                        logger.remove(file_handler)
                    except Exception as e:
                        print(f"Warning: Error removing handlers for session {session_id}: {e}")
                    del cls._handlers[session_id]
                
                # 移除logger
                del cls._loggers[session_id]
                
            except Exception as e:
                print(f"Warning: Error closing session logger {session_id}: {e}")
    
    @classmethod
    def cleanup_old_logs(cls, days_to_keep: int = 7):
        """清理旧日志文件"""
        from datetime import timedelta
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            sessions_dir = Path("logs/sessions")
            
            if not sessions_dir.exists():
                return
            
            deleted_count = 0
            for session_dir in sessions_dir.iterdir():
                if session_dir.is_dir():
                    for log_file in session_dir.glob("*.log"):
                        try:
                            if log_file.stat().st_mtime < cutoff_date.timestamp():
                                log_file.unlink()
                                deleted_count += 1
                        except Exception:
                            continue
                    
                    # 删除空目录
                    try:
                        if not any(session_dir.iterdir()):
                            session_dir.rmdir()
                    except Exception:
                        continue
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old log files")
                
        except Exception as e:
            print(f"Warning: Error during log cleanup: {e}")

def get_session_logger(session_id: str):
    """获取session专用logger的便捷函数"""
    return SessionLogger.get_logger(session_id) 