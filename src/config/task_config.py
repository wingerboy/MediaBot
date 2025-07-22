"""
任务配置管理模块
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json
from pathlib import Path

class ActionType(Enum):
    """行为类型枚举"""
    FOLLOW = "follow"
    LIKE = "like"
    COMMENT = "comment"
    RETWEET = "retweet"
    BROWSE = "browse"

@dataclass
class ActionConfig:
    """单个行为配置"""
    action_type: ActionType
    count: int = 10                    # 执行次数
    min_interval: float = 5.0          # 最小时间间隔(秒)
    max_interval: float = 15.0         # 最大时间间隔(秒)
    enabled: bool = True               # 是否启用
    
    # 评论相关参数
    comment_templates: List[str] = field(default_factory=list)  # 兼容旧字段名
    template_comments: List[str] = field(default_factory=list)  # 新字段名
    use_ai_comment: bool = False       # 是否使用AI生成评论
    ai_comment_fallback: str = "template"  # AI失败时的备用方案: "template" 或 "skip"
    
    # 关注相关参数
    follow_back_ratio: float = 0.3     # 关注回关率
    
    # 条件判断参数
    conditions: Dict[str, Any] = field(default_factory=dict)  # 执行条件
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果template_comments为空但comment_templates有值，则复制过来
        if not self.template_comments and self.comment_templates:
            self.template_comments = self.comment_templates
        # 如果comment_templates为空但template_comments有值，则复制过来（保持兼容性）
        elif not self.comment_templates and self.template_comments:
            self.comment_templates = self.template_comments
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'action_type': self.action_type.value,
            'count': self.count,
            'min_interval': self.min_interval,
            'max_interval': self.max_interval,
            'enabled': self.enabled,
            'comment_templates': self.comment_templates,
            'template_comments': self.template_comments,
            'use_ai_comment': self.use_ai_comment,
            'ai_comment_fallback': self.ai_comment_fallback,
            'follow_back_ratio': self.follow_back_ratio,
            'conditions': self.conditions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionConfig':
        """从字典创建实例"""
        # 创建数据副本避免修改原始数据
        data_copy = data.copy()
        data_copy['action_type'] = ActionType(data_copy['action_type'])
        
        # 处理字段兼容性
        if 'template_comments' not in data_copy and 'comment_templates' in data_copy:
            data_copy['template_comments'] = data_copy['comment_templates']
        
        # 设置默认值
        data_copy.setdefault('comment_templates', [])
        data_copy.setdefault('template_comments', [])
        data_copy.setdefault('use_ai_comment', False)
        data_copy.setdefault('ai_comment_fallback', 'template')
        data_copy.setdefault('follow_back_ratio', 0.3)
        data_copy.setdefault('conditions', {})
        data_copy.setdefault('enabled', True)
        
        return cls(**data_copy)

@dataclass
class TargetConfig:
    """目标领域配置"""
    source: str = "timeline"                                      # 内容源: "timeline", "search", "user"
    keywords: List[str] = field(default_factory=list)            # 搜索关键词
    hashtags: List[str] = field(default_factory=list)            # 目标话题标签
    users: List[str] = field(default_factory=list)               # 目标用户
    languages: List[str] = field(default_factory=lambda: ['en', 'zh'])  # 语言限制
    content_languages: List[str] = field(default_factory=lambda: ['en', 'zh'])  # 内容语言限制（兼容字段）
    
    # 搜索排序设置
    is_live: bool = False             # True=最新推文, False=热门推文 (仅在搜索模式下有效)
    
    # 内容过滤
    min_likes: int = 0                 # 最小点赞数
    max_age_hours: int = 24           # 内容最大年龄(小时)
    exclude_keywords: List[str] = field(default_factory=list)  # 排除关键词
    
    def __post_init__(self):
        """初始化后处理"""
        # 统一语言设置
        if not self.languages and self.content_languages:
            self.languages = self.content_languages
        elif not self.content_languages and self.languages:
            self.content_languages = self.languages
        
        # 验证hashtags和keywords是否冲突
        self._validate_content_source()
    
    def _validate_content_source(self):
        """验证内容源配置"""
        if self.hashtags and self.keywords:
            raise ValueError("hashtags和keywords不能同时使用，它们是互斥的内容获取方式。请选择其中一种。")
        
        if not self.hashtags and not self.keywords and self.source not in ["timeline", "home"]:
            print("⚠️  警告: 未配置hashtags或keywords，将使用主页时间线作为内容源")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source': self.source,
            'keywords': self.keywords,
            'hashtags': self.hashtags,
            'users': self.users,
            'languages': self.languages,
            'content_languages': self.content_languages,
            'is_live': self.is_live,
            'min_likes': self.min_likes,
            'max_age_hours': self.max_age_hours,
            'exclude_keywords': self.exclude_keywords
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TargetConfig':
        """从字典创建实例"""
        # 创建数据副本并设置默认值
        data_copy = data.copy()
        data_copy.setdefault('source', 'timeline')
        data_copy.setdefault('keywords', [])
        data_copy.setdefault('hashtags', [])
        data_copy.setdefault('users', [])
        data_copy.setdefault('languages', ['en', 'zh'])
        data_copy.setdefault('content_languages', data_copy['languages'])
        data_copy.setdefault('is_live', False)
        data_copy.setdefault('min_likes', 0)
        data_copy.setdefault('max_age_hours', 24)
        data_copy.setdefault('exclude_keywords', [])
        
        return cls(**data_copy)

@dataclass
class SessionConfig:
    """单次会话配置"""
    session_id: str                    # 会话ID
    name: str                         # 任务名称
    description: str = ""             # 任务描述
    
    # 行为配置
    actions: List[ActionConfig] = field(default_factory=list)
    
    # 目标配置
    target: TargetConfig = field(default_factory=TargetConfig)
    
    # 会话限制
    max_duration_minutes: int = 60    # 最大执行时间(分钟)
    max_total_actions: int = 100      # 最大总行为数
    
    # 安全设置
    randomize_intervals: bool = True   # 随机化间隔
    respect_rate_limits: bool = True   # 遵守速率限制
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'name': self.name,
            'description': self.description,
            'actions': [action.to_dict() for action in self.actions],
            'target': self.target.to_dict(),
            'max_duration_minutes': self.max_duration_minutes,
            'max_total_actions': self.max_total_actions,
            'randomize_intervals': self.randomize_intervals,
            'respect_rate_limits': self.respect_rate_limits
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionConfig':
        """从字典创建实例"""
        actions = [ActionConfig.from_dict(action_data) for action_data in data.get('actions', [])]
        target = TargetConfig.from_dict(data.get('target', {}))
        
        return cls(
            session_id=data['session_id'],
            name=data['name'],
            description=data.get('description', ''),
            actions=actions,
            target=target,
            max_duration_minutes=data.get('max_duration_minutes', 60),
            max_total_actions=data.get('max_total_actions', 100),
            randomize_intervals=data.get('randomize_intervals', True),
            respect_rate_limits=data.get('respect_rate_limits', True)
        )
    
    def save_to_file(self, filepath: Path) -> None:
        """保存配置到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> 'SessionConfig':
        """从文件加载配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

class TaskConfigManager:
    """任务配置管理器"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path("config/tasks")
        self.config_dir.mkdir(exist_ok=True, parents=True)
    
    def create_default_config(self, session_id: str, name: str) -> SessionConfig:
        """创建默认配置"""
        # 默认行为配置
        actions = [
            ActionConfig(
                action_type=ActionType.LIKE,
                count=20,
                min_interval=3.0,
                max_interval=8.0,
                conditions={
                    'min_like_count': 10,      # 至少10个赞才点赞
                    'max_like_count': 10000,   # 最多10K赞以下才点赞（避免热门内容）
                    'min_view_count': 100,     # 至少100浏览量
                    'has_media': None,         # 不限制是否有媒体
                    'verified_only': None,     # 不限制验证状态
                    'min_content_length': 20   # 至少20字符内容
                }
            ),
            ActionConfig(
                action_type=ActionType.FOLLOW,
                count=5,
                min_interval=10.0,
                max_interval=20.0,
                conditions={
                    'min_like_count': 50,      # 关注高质量内容作者
                    'min_view_count': 500,     # 较高浏览量
                    'verified_only': False,    # 不限制仅验证用户
                    'exclude_verified': False, # 不排除验证用户
                    'min_content_length': 50   # 较长内容说明用户活跃
                }
            ),
            ActionConfig(
                action_type=ActionType.COMMENT,
                count=3,
                min_interval=15.0,
                max_interval=30.0,
                conditions={
                    'min_like_count': 20,      # 有一定热度才评论
                    'max_like_count': 5000,    # 避免过热内容
                    'min_reply_count': 2,      # 已有一些讨论
                    'max_reply_count': 100,    # 避免讨论过热
                    'min_content_length': 30,  # 有实质内容
                    'has_media': False         # 优先评论纯文本内容
                },
                comment_templates=[
                    "Great content! 👍",
                    "Thanks for sharing!",
                    "Interesting perspective 🤔",
                    "Love this! 💯",
                    "Very insightful 📚"
                ]
            )
        ]
        
        # 默认目标配置
        target = TargetConfig(
            keywords=["AI", "Machine Learning", "Technology"],
            hashtags=["#AI", "#ML", "#Tech"],
            min_likes=10,
            max_age_hours=24
        )
        
        return SessionConfig(
            session_id=session_id,
            name=name,
            actions=actions,
            target=target
        )
    
    def save_config(self, config: SessionConfig) -> Path:
        """保存配置"""
        filepath = self.config_dir / f"{config.session_id}.json"
        config.save_to_file(filepath)
        return filepath
    
    def load_config(self, session_id: str) -> Optional[SessionConfig]:
        """加载配置"""
        filepath = self.config_dir / f"{session_id}.json"
        if filepath.exists():
            return SessionConfig.load_from_file(filepath)
        return None
    
    def list_configs(self) -> List[str]:
        """列出所有配置"""
        return [f.stem for f in self.config_dir.glob("*.json")]
    
    def delete_config(self, session_id: str) -> bool:
        """删除配置"""
        filepath = self.config_dir / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

@dataclass 
class ActionConditions:
    """行为执行条件"""
    # 互动数据条件
    min_like_count: Optional[int] = None        # 最小点赞数
    max_like_count: Optional[int] = None        # 最大点赞数
    min_retweet_count: Optional[int] = None     # 最小转发数
    max_retweet_count: Optional[int] = None     # 最大转发数
    min_reply_count: Optional[int] = None       # 最小回复数
    max_reply_count: Optional[int] = None       # 最大回复数
    min_view_count: Optional[int] = None        # 最小浏览量
    max_view_count: Optional[int] = None        # 最大浏览量
    
    # 用户条件
    min_follower_count: Optional[int] = None    # 最小粉丝数
    max_follower_count: Optional[int] = None    # 最大粉丝数
    verified_only: Optional[bool] = None        # 仅验证用户
    exclude_verified: Optional[bool] = None     # 排除验证用户
    
    # 内容条件
    has_media: Optional[bool] = None            # 是否包含媒体
    media_types: List[str] = field(default_factory=list)  # 媒体类型 ['image', 'video', 'gif']
    min_content_length: Optional[int] = None    # 最小内容长度
    max_content_length: Optional[int] = None    # 最大内容长度
    exclude_keywords: List[str] = field(default_factory=list)  # 排除关键词
    
    # 时间条件
    max_age_hours: Optional[int] = None         # 最大发布时间(小时)
    
    def check_conditions(self, tweet_data: Dict[str, Any]) -> bool:
        """检查是否满足执行条件"""
        try:
            # 检查互动数据条件
            if not self._check_interaction_conditions(tweet_data):
                return False
            
            # 检查用户条件
            if not self._check_user_conditions(tweet_data):
                return False
            
            # 检查内容条件
            if not self._check_content_conditions(tweet_data):
                return False
            
            # 检查时间条件
            if not self._check_time_conditions(tweet_data):
                return False
            
            return True
            
        except Exception as e:
            # 如果检查过程出错，默认不执行
            return False
    
    def _check_interaction_conditions(self, tweet_data: Dict[str, Any]) -> bool:
        """检查互动数据条件"""
        # 点赞数检查
        if self.min_like_count is not None or self.max_like_count is not None:
            like_count = self._parse_count(tweet_data.get('like_count', '0'))
            if self.min_like_count is not None and like_count < self.min_like_count:
                return False
            if self.max_like_count is not None and like_count > self.max_like_count:
                return False
        
        # 转发数检查
        if self.min_retweet_count is not None or self.max_retweet_count is not None:
            retweet_count = self._parse_count(tweet_data.get('retweet_count', '0'))
            if self.min_retweet_count is not None and retweet_count < self.min_retweet_count:
                return False
            if self.max_retweet_count is not None and retweet_count > self.max_retweet_count:
                return False
        
        # 回复数检查
        if self.min_reply_count is not None or self.max_reply_count is not None:
            reply_count = self._parse_count(tweet_data.get('reply_count', '0'))
            if self.min_reply_count is not None and reply_count < self.min_reply_count:
                return False
            if self.max_reply_count is not None and reply_count > self.max_reply_count:
                return False
        
        # 浏览量检查
        if self.min_view_count is not None or self.max_view_count is not None:
            view_count = self._parse_count(tweet_data.get('view_count', '0'))
            if self.min_view_count is not None and view_count < self.min_view_count:
                return False
            if self.max_view_count is not None and view_count > self.max_view_count:
                return False
        
        return True
    
    def _check_user_conditions(self, tweet_data: Dict[str, Any]) -> bool:
        """检查用户条件"""
        # 验证状态检查
        is_verified = tweet_data.get('is_verified', False)
        if self.verified_only is True and not is_verified:
            return False
        if self.exclude_verified is True and is_verified:
            return False
        
        # 粉丝数检查（如果有的话）
        if self.min_follower_count is not None or self.max_follower_count is not None:
            follower_count = tweet_data.get('follower_count')
            if follower_count is not None:
                if self.min_follower_count is not None and follower_count < self.min_follower_count:
                    return False
                if self.max_follower_count is not None and follower_count > self.max_follower_count:
                    return False
        
        return True
    
    def _check_content_conditions(self, tweet_data: Dict[str, Any]) -> bool:
        """检查内容条件"""
        # 媒体条件检查
        if self.has_media is not None:
            has_any_media = any([
                tweet_data.get('has_images', False),
                tweet_data.get('has_video', False), 
                tweet_data.get('has_gif', False)
            ])
            if self.has_media and not has_any_media:
                return False
            if not self.has_media and has_any_media:
                return False
        
        # 特定媒体类型检查
        if self.media_types:
            media_present = []
            if tweet_data.get('has_images', False):
                media_present.append('image')
            if tweet_data.get('has_video', False):
                media_present.append('video')
            if tweet_data.get('has_gif', False):
                media_present.append('gif')
            
            # 检查是否有要求的媒体类型
            if not any(media_type in media_present for media_type in self.media_types):
                return False
        
        # 内容长度检查
        content = tweet_data.get('content', '')
        content_length = len(content)
        
        if self.min_content_length is not None and content_length < self.min_content_length:
            return False
        if self.max_content_length is not None and content_length > self.max_content_length:
            return False
        
        # 排除关键词检查
        if self.exclude_keywords:
            content_text = content.lower()
            for keyword in self.exclude_keywords:
                if keyword.lower() in content_text:
                    return False
        
        return True
    
    def _check_time_conditions(self, tweet_data: Dict[str, Any]) -> bool:
        """检查时间条件"""
        if self.max_age_hours is not None:
            # 这里需要解析推文时间，暂时跳过
            # 可以在后续实现时间解析逻辑
            pass
        
        return True
    
    def _parse_count(self, count_str: str) -> int:
        """解析数字字符串为整数"""
        try:
            if isinstance(count_str, int):
                return count_str
            if isinstance(count_str, str):
                # 移除逗号等分隔符
                count_str = count_str.replace(',', '').strip()
                if count_str.isdigit():
                    return int(count_str)
            return 0
        except:
            return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'min_like_count': self.min_like_count,
            'max_like_count': self.max_like_count,
            'min_retweet_count': self.min_retweet_count,
            'max_retweet_count': self.max_retweet_count,
            'min_reply_count': self.min_reply_count,
            'max_reply_count': self.max_reply_count,
            'min_view_count': self.min_view_count,
            'max_view_count': self.max_view_count,
            'min_follower_count': self.min_follower_count,
            'max_follower_count': self.max_follower_count,
            'verified_only': self.verified_only,
            'exclude_verified': self.exclude_verified,
            'has_media': self.has_media,
            'media_types': self.media_types,
            'min_content_length': self.min_content_length,
            'max_content_length': self.max_content_length,
            'exclude_keywords': self.exclude_keywords,
            'max_age_hours': self.max_age_hours
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionConditions':
        """从字典创建实例"""
        return cls(**data)

# 全局配置管理器实例
config_manager = TaskConfigManager() 