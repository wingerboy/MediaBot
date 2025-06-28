"""
账号管理模块 - 支持多账号配置和管理
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class AccountConfig:
    """账号配置"""
    account_id: str                    # 账号ID（唯一标识）
    username: str = ""                 # Twitter用户名  
    display_name: str = ""             # 显示名称
    email: str = ""                    # 邮箱
    cookies_file: str = ""             # cookies文件路径
    
    # 状态信息
    is_active: bool = True            # 是否激活
    last_used: Optional[str] = None   # 最后使用时间
    usage_count: int = 0              # 使用次数
    notes: str = ""                   # 备注
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.cookies_file:
            self.cookies_file = f"data/cookies/cookies_{self.account_id}.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountConfig':
        """从字典创建实例"""
        # 兼容旧格式，忽略不需要的字段
        valid_fields = {
            'account_id', 'username', 'display_name', 'email', 'cookies_file',
            'is_active', 'last_used', 'usage_count', 'notes'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def is_available(self) -> bool:
        """检查账号是否可用"""
        return self.is_active
    
    def update_usage(self):
        """更新使用信息"""
        self.last_used = datetime.now().isoformat()
        self.usage_count += 1

class AccountManager:
    """账号管理器"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path("data/accounts")
        self.config_file = self.config_dir / "accounts.json"
        self.accounts: Dict[str, AccountConfig] = {}
        self.logger = logging.getLogger(__name__)
        
        # 确保目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self.load_accounts()
    
    def load_accounts(self):
        """加载账号配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.accounts = {
                    account_id: AccountConfig.from_dict(account_data)
                    for account_id, account_data in data.items()
                }
                
                self.logger.info(f"加载了 {len(self.accounts)} 个账号配置")
            else:
                self.logger.info("未找到账号配置文件，使用空配置")
                
        except Exception as e:
            self.logger.error(f"加载账号配置失败: {e}")
            self.accounts = {}
    
    def save_accounts(self):
        """保存账号配置"""
        try:
            data = {
                account_id: account.to_dict()
                for account_id, account in self.accounts.items()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"保存了 {len(self.accounts)} 个账号配置")
            
        except Exception as e:
            self.logger.error(f"保存账号配置失败: {e}")
    
    def add_or_update_account(self, account_id: str, **kwargs) -> AccountConfig:
        """添加或更新账号"""
        if account_id in self.accounts:
            # 更新现有账号
            account = self.accounts[account_id]
            for key, value in kwargs.items():
                if hasattr(account, key) and value:
                    setattr(account, key, value)
        else:
            # 创建新账号
            account = AccountConfig(account_id=account_id, **kwargs)
            self.accounts[account_id] = account
        
        self.save_accounts()
        self.logger.info(f"账号 {account_id} 信息已更新")
        return account
    
    def get_account(self, account_id: str) -> Optional[AccountConfig]:
        """获取账号配置"""
        return self.accounts.get(account_id)
    
    def list_accounts(self) -> List[AccountConfig]:
        """列出所有账号"""
        return list(self.accounts.values())
    
    def get_available_accounts(self) -> List[AccountConfig]:
        """获取可用账号列表"""
        return [account for account in self.accounts.values() if account.is_available()]
    
    def update_account_usage(self, account_id: str):
        """更新账号使用信息"""
        account = self.get_account(account_id)
        if account:
            account.update_usage()
            self.save_accounts()
    
    def get_account_stats(self) -> Dict[str, Any]:
        """获取账号统计信息"""
        total = len(self.accounts)
        active = len([a for a in self.accounts.values() if a.is_active])
        available = len(self.get_available_accounts())
        
        return {
            "total": total,
            "active": active,
            "available": available
        }

# 全局账号管理器实例
account_manager = AccountManager() 