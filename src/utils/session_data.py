"""
Session 数据记录管理器
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class ActionResult(Enum):
    """行为执行结果枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class ActionRecord:
    """单个行为记录"""
    timestamp: str
    action_type: str
    target_type: str        # tweet, user, hashtag等
    target_id: str
    result: str
    details: Dict[str, Any]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

@dataclass 
class SessionStats:
    """Session统计信息"""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    skipped_actions: int = 0
    error_actions: int = 0
    
    # 分类统计
    likes_count: int = 0
    follows_count: int = 0
    comments_count: int = 0
    retweets_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

class SessionDataManager:
    """Session数据管理器"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.data_dir = Path("data/sessions") / session_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.actions_file = self.data_dir / f"actions_{timestamp}.json"
        self.stats_file = self.data_dir / f"stats_{timestamp}.json"
        self.targets_file = self.data_dir / f"targets_{timestamp}.json"
        
        # 内存数据
        self.actions: List[ActionRecord] = []
        self.stats = SessionStats(
            session_id=session_id,
            start_time=datetime.now().isoformat()
        )
        self.discovered_targets: Dict[str, Any] = {}
        
        # 初始化文件
        self._init_files()
    
    def _init_files(self):
        """初始化数据文件"""
        # 创建空的actions文件
        with open(self.actions_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        # 保存初始统计
        self.save_stats()
        
        # 创建空的targets文件
        with open(self.targets_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    
    def record_action(self, action_type: str, target_type: str, target_id: str, 
                     result: ActionResult, details: Dict[str, Any] = None, 
                     error_message: str = None):
        """记录单个行为"""
        record = ActionRecord(
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            result=result.value,
            details=details or {},
            error_message=error_message
        )
        
        self.actions.append(record)
        self._update_stats(record)
        self._save_action(record)
    
    def _update_stats(self, record: ActionRecord):
        """更新统计信息"""
        self.stats.total_actions += 1
        
        # 按结果统计
        if record.result == ActionResult.SUCCESS.value:
            self.stats.successful_actions += 1
        elif record.result == ActionResult.FAILED.value:
            self.stats.failed_actions += 1
        elif record.result == ActionResult.SKIPPED.value:
            self.stats.skipped_actions += 1
        elif record.result == ActionResult.ERROR.value:
            self.stats.error_actions += 1
        
        # 按类型统计
        if record.action_type == "like":
            self.stats.likes_count += 1
        elif record.action_type == "follow":
            self.stats.follows_count += 1
        elif record.action_type == "comment":
            self.stats.comments_count += 1
        elif record.action_type == "retweet":
            self.stats.retweets_count += 1
    
    def _save_action(self, record: ActionRecord):
        """保存单个行为记录到文件"""
        # 读取现有数据
        try:
            with open(self.actions_file, 'r', encoding='utf-8') as f:
                actions_data = json.load(f)
        except:
            actions_data = []
        
        # 添加新记录
        actions_data.append(record.to_dict())
        
        # 写回文件
        with open(self.actions_file, 'w', encoding='utf-8') as f:
            json.dump(actions_data, f, indent=2, ensure_ascii=False)
    
    def save_stats(self):
        """保存统计信息"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats.to_dict(), f, indent=2, ensure_ascii=False)
    
    def record_target(self, target_type: str, target_id: str, target_data: Dict[str, Any]):
        """记录发现的目标"""
        if target_type not in self.discovered_targets:
            self.discovered_targets[target_type] = {}
        
        self.discovered_targets[target_type][target_id] = {
            **target_data,
            'discovered_at': datetime.now().isoformat()
        }
        
        # 保存到文件
        with open(self.targets_file, 'w', encoding='utf-8') as f:
            json.dump(self.discovered_targets, f, indent=2, ensure_ascii=False)
    
    def get_action_summary(self) -> Dict[str, Any]:
        """获取行为摘要"""
        return {
            'total_actions': len(self.actions),
            'success_rate': self.stats.successful_actions / max(self.stats.total_actions, 1),
            'actions_by_type': {
                'likes': self.stats.likes_count,
                'follows': self.stats.follows_count,
                'comments': self.stats.comments_count,
                'retweets': self.stats.retweets_count
            },
            'results_breakdown': {
                'successful': self.stats.successful_actions,
                'failed': self.stats.failed_actions,
                'skipped': self.stats.skipped_actions,
                'error': self.stats.error_actions
            }
        }
    
    def close_session(self):
        """关闭session，保存最终数据"""
        self.stats.end_time = datetime.now().isoformat()
        self.save_stats()
        
        # 生成session摘要
        summary = self.get_action_summary()
        summary_file = self.data_dir / "session_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_session_data(cls, session_id: str, timestamp: str = None) -> Optional['SessionDataManager']:
        """加载指定session的数据"""
        data_dir = Path("data/sessions") / session_id
        if not data_dir.exists():
            return None
        
        # 如果没有指定时间戳，使用最新的
        if timestamp is None:
            stats_files = list(data_dir.glob("stats_*.json"))
            if not stats_files:
                return None
            timestamp = max(stats_files).stem.split('_', 1)[1]
        
        # 创建实例但不初始化新文件
        instance = cls.__new__(cls)
        instance.session_id = session_id
        instance.data_dir = data_dir
        
        # 加载数据
        try:
            actions_file = data_dir / f"actions_{timestamp}.json"
            with open(actions_file, 'r', encoding='utf-8') as f:
                actions_data = json.load(f)
            instance.actions = [ActionRecord(**data) for data in actions_data]
            
            stats_file = data_dir / f"stats_{timestamp}.json"
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats_data = json.load(f)
            instance.stats = SessionStats(**stats_data)
            
            targets_file = data_dir / f"targets_{timestamp}.json"
            with open(targets_file, 'r', encoding='utf-8') as f:
                instance.discovered_targets = json.load(f)
            
            return instance
        except Exception as e:
            print(f"Error loading session data: {e}")
            return None
    
    @classmethod
    def list_sessions(cls) -> List[str]:
        """列出所有session"""
        sessions_dir = Path("data/sessions")
        if not sessions_dir.exists():
            return []
        
        return [d.name for d in sessions_dir.iterdir() if d.is_dir()]
    
    @classmethod
    def cleanup_old_data(cls, days_to_keep: int = 30):
        """清理旧数据"""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        sessions_dir = Path("data/sessions")
        
        if not sessions_dir.exists():
            return
        
        deleted_count = 0
        for session_dir in sessions_dir.iterdir():
            if session_dir.is_dir():
                for data_file in session_dir.glob("*.json"):
                    if data_file.stat().st_mtime < cutoff_date.timestamp():
                        data_file.unlink()
                        deleted_count += 1
                
                # 删除空目录
                if not any(session_dir.iterdir()):
                    session_dir.rmdir()
        
        return deleted_count 