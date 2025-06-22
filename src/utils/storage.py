"""
本地存储工具
"""
import json
import pickle
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

class LocalStorage:
    """本地存储管理器"""
    
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def save_json(self, filename: str, data: Dict[str, Any]) -> bool:
        """保存JSON数据"""
        try:
            filepath = self.storage_dir / f"{filename}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            print(f"保存JSON失败: {e}")
            return False
    
    def load_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """加载JSON数据"""
        try:
            filepath = self.storage_dir / f"{filename}.json"
            if not filepath.exists():
                return None
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载JSON失败: {e}")
            return None
    
    def save_pickle(self, filename: str, data: Any) -> bool:
        """保存Pickle数据"""
        try:
            filepath = self.storage_dir / f"{filename}.pkl"
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"保存Pickle失败: {e}")
            return False
    
    def load_pickle(self, filename: str) -> Any:
        """加载Pickle数据"""
        try:
            filepath = self.storage_dir / f"{filename}.pkl"
            if not filepath.exists():
                return None
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"加载Pickle失败: {e}")
            return None
    
    def save_cookies(self, cookies: list, filename: str = "cookies") -> bool:
        """保存浏览器cookies"""
        return self.save_json(filename, {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat()
        })
    
    def load_cookies(self, filename: str = "cookies") -> Optional[list]:
        """加载浏览器cookies"""
        data = self.load_json(filename)
        return data.get("cookies") if data else None
    
    def exists(self, filename: str, format: str = "json") -> bool:
        """检查文件是否存在"""
        ext = ".json" if format == "json" else ".pkl"
        filepath = self.storage_dir / f"{filename}{ext}"
        return filepath.exists()

# 创建全局存储实例
storage = LocalStorage() 