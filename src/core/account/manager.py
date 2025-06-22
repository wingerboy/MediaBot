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
    username: str                      # Twitter用户名
    display_name: str                  # 显示名称
    email: str                         # 邮箱
    password: str                      # 密码
    cookies_file: str                  # cookies文件路径
    
    # 状态信息
    is_active: bool = True            # 是否激活
    last_used: Optional[str] = None   # 最后使用时间
    cooldown_until: Optional[str] = None  # 冷却结束时间
    usage_count: int = 0              # 使用次数
    notes: str = ""                   # 备注
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountConfig':
        """从字典创建实例"""
        return cls(**data)
    
    def is_available(self) -> bool:
        """检查账号是否可用"""
        if not self.is_active:
            return False
        
        # 检查冷却时间
        if self.cooldown_until:
            cooldown_time = datetime.fromisoformat(self.cooldown_until)
            if datetime.now() < cooldown_time:
                return False
        
        return True
    
    def set_cooldown(self, hours: int = 2):
        """设置冷却时间"""
        cooldown_time = datetime.now() + timedelta(hours=hours)
        self.cooldown_until = cooldown_time.isoformat()
    
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
    
    def add_account(self, account: AccountConfig) -> bool:
        """添加账号"""
        try:
            if account.account_id in self.accounts:
                self.logger.warning(f"账号 {account.account_id} 已存在，将覆盖")
            
            self.accounts[account.account_id] = account
            self.save_accounts()
            
            self.logger.info(f"添加账号成功: {account.account_id} (@{account.username})")
            return True
            
        except Exception as e:
            self.logger.error(f"添加账号失败: {e}")
            return False
    
    def remove_account(self, account_id: str) -> bool:
        """删除账号"""
        try:
            if account_id in self.accounts:
                account = self.accounts.pop(account_id)
                self.save_accounts()
                
                self.logger.info(f"删除账号成功: {account_id} (@{account.username})")
                return True
            else:
                self.logger.warning(f"账号 {account_id} 不存在")
                return False
                
        except Exception as e:
            self.logger.error(f"删除账号失败: {e}")
            return False
    
    def get_account(self, account_id: str) -> Optional[AccountConfig]:
        """获取账号配置"""
        return self.accounts.get(account_id)
    
    def list_accounts(self) -> List[AccountConfig]:
        """列出所有账号"""
        return list(self.accounts.values())
    
    def get_available_accounts(self) -> List[AccountConfig]:
        """获取可用账号列表"""
        return [account for account in self.accounts.values() if account.is_available()]
    
    def get_next_account(self, exclude_ids: List[str] = None) -> Optional[AccountConfig]:
        """获取下一个可用账号"""
        exclude_ids = exclude_ids or []
        
        available_accounts = [
            account for account in self.get_available_accounts()
            if account.account_id not in exclude_ids
        ]
        
        if not available_accounts:
            return None
        
        # 按最后使用时间排序，优先使用最久未使用的账号
        available_accounts.sort(key=lambda x: x.last_used or "1900-01-01")
        
        return available_accounts[0]
    
    def update_account_usage(self, account_id: str, set_cooldown: bool = True):
        """更新账号使用信息"""
        account = self.get_account(account_id)
        if account:
            account.update_usage()
            if set_cooldown:
                account.set_cooldown()
            self.save_accounts()
    
    def set_account_status(self, account_id: str, is_active: bool):
        """设置账号状态"""
        account = self.get_account(account_id)
        if account:
            account.is_active = is_active
            self.save_accounts()
            
            status = "激活" if is_active else "禁用"
            self.logger.info(f"账号 {account_id} 已{status}")
    
    def clear_cooldowns(self):
        """清除所有账号的冷却时间"""
        for account in self.accounts.values():
            account.cooldown_until = None
        self.save_accounts()
        self.logger.info("已清除所有账号的冷却时间")
    
    def get_account_stats(self) -> Dict[str, Any]:
        """获取账号统计信息"""
        total = len(self.accounts)
        active = len([a for a in self.accounts.values() if a.is_active])
        available = len(self.get_available_accounts())
        in_cooldown = len([a for a in self.accounts.values() if a.cooldown_until])
        
        return {
            "total": total,
            "active": active,
            "available": available,
            "in_cooldown": in_cooldown
        }

# 全局账号管理器实例
account_manager = AccountManager() 