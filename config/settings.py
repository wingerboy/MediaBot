"""
MediaBot 配置文件
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings:
    """配置类"""
    
    def __init__(self):
        # 项目路径
        self.PROJECT_ROOT = Path(__file__).parent.parent
        self.DATA_DIR = self.PROJECT_ROOT / "data"
        self.LOGS_DIR = self.PROJECT_ROOT / "logs"
        
        # 浏览器设置
        self.HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"
        self.BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")
        self.USER_AGENT = os.getenv("USER_AGENT")
        
        # Twitter设置
        self.TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
        self.TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
        self.TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
        
        # 行为设置
        self.MIN_DELAY = float(os.getenv("MIN_DELAY", "2.0"))
        self.MAX_DELAY = float(os.getenv("MAX_DELAY", "5.0"))
        self.PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30000"))
        
        # 安全设置
        self.ENABLE_STEALTH = os.getenv("ENABLE_STEALTH", "True").lower() == "true"
        self.RANDOMIZE_BEHAVIOR = os.getenv("RANDOMIZE_BEHAVIOR", "True").lower() == "true"
        
        # DeepSeek AI配置
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))
        self.DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "100"))
        self.DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "30"))
        
        # 确保目录存在
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)

# 创建全局设置实例
settings = Settings() 