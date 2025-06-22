"""
AI服务模块 - 接入DeepSeek大模型生成智能评论
"""
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AIConfig:
    """AI配置"""
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 100
    timeout: int = 30

class AIService:
    """AI服务类"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def generate_comment(self, tweet_data: Dict[str, Any]) -> Optional[str]:
        """
        根据推文内容生成智能评论
        
        Args:
            tweet_data: 推文数据，包含content、username、like_count等信息
            
        Returns:
            生成的评论内容，失败时返回None
        """
        try:
            # 构建提示词
            prompt = self._build_comment_prompt(tweet_data)
            
            # 调用AI API
            response = await self._call_deepseek_api(prompt)
            
            if response:
                # 后处理生成的评论
                comment = self._post_process_comment(response)
                self.logger.info(f"AI生成评论成功: {comment}")
                return comment
            
            return None
            
        except Exception as e:
            self.logger.error(f"AI生成评论失败: {e}")
            return None
    
    def _build_comment_prompt(self, tweet_data: Dict[str, Any]) -> str:
        """构建评论生成的提示词"""
        content = tweet_data.get('content', '')
        username = tweet_data.get('username', '')
        like_count = tweet_data.get('like_count', '0')
        retweet_count = tweet_data.get('retweet_count', '0')
        is_verified = tweet_data.get('is_verified', False)
        
        # 检测内容语言
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in content)
        
        if is_chinese:
            # 中文提示词
            prompt = f"""请为以下推文生成一个自然、友善的回复评论：

推文作者: @{username} {'(已验证)' if is_verified else ''}
推文内容: {content}
互动数据: {like_count}赞 {retweet_count}转发

要求:
1. 回复要自然、友善，符合社交媒体的表达习惯
2. 长度控制在50字以内
3. 可以适当使用emoji增强表达效果
4. 不要过度夸赞，保持真诚
5. 避免争议性话题
6. 直接输出评论内容，不要添加引号或解释

评论:"""
        else:
            # 英文提示词
            prompt = f"""Please generate a natural, friendly reply comment for the following tweet:

Tweet author: @{username} {'(verified)' if is_verified else ''}
Tweet content: {content}
Engagement: {like_count} likes, {retweet_count} retweets

Requirements:
1. Reply should be natural and friendly, fitting social media expression habits
2. Keep it under 50 characters
3. Use emojis appropriately to enhance expression
4. Don't over-praise, stay genuine
5. Avoid controversial topics
6. Output the comment directly without quotes or explanations

Comment:"""
        
        return prompt
    
    async def _call_deepseek_api(self, prompt: str) -> Optional[str]:
        """调用DeepSeek API"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False
        }
        
        try:
            async with self.session.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return content.strip()
                else:
                    error_text = await response.text()
                    self.logger.error(f"DeepSeek API错误 {response.status}: {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            self.logger.error("DeepSeek API请求超时")
            return None
        except Exception as e:
            self.logger.error(f"调用DeepSeek API异常: {e}")
            return None
    
    def _post_process_comment(self, raw_comment: str) -> str:
        """后处理生成的评论"""
        if not raw_comment:
            return ""
        
        # 清理格式
        comment = raw_comment.strip()
        
        # 移除可能的引号
        if comment.startswith('"') and comment.endswith('"'):
            comment = comment[1:-1]
        if comment.startswith("'") and comment.endswith("'"):
            comment = comment[1:-1]
        
        # 移除可能的前缀
        prefixes_to_remove = [
            "评论:", "Comment:", "回复:", "Reply:", 
            "评论：", "Comment：", "回复：", "Reply："
        ]
        for prefix in prefixes_to_remove:
            if comment.startswith(prefix):
                comment = comment[len(prefix):].strip()
        
        # 长度限制 (Twitter评论限制)
        if len(comment) > 280:
            comment = comment[:277] + "..."
        
        return comment

class AIServiceManager:
    """AI服务管理器"""
    
    _instance = None
    _ai_service = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, config: AIConfig):
        """初始化AI服务"""
        self._config = config
        self.logger = logging.getLogger(__name__)
    
    async def get_ai_service(self) -> AIService:
        """获取AI服务实例"""
        if not hasattr(self, '_config'):
            raise RuntimeError("AI服务未初始化，请先调用initialize()")
        
        return AIService(self._config)
    
    async def generate_comment(self, tweet_data: Dict[str, Any]) -> Optional[str]:
        """生成评论的便捷方法"""
        try:
            async with await self.get_ai_service() as ai_service:
                return await ai_service.generate_comment(tweet_data)
        except Exception as e:
            self.logger.error(f"AI评论生成失败: {e}")
            return None

# 全局AI服务管理器实例
ai_service_manager = AIServiceManager() 