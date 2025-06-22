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
            system_prompt, user_prompt = self._build_comment_prompt(tweet_data)
            
            # 调用AI API
            response = await self._call_deepseek_api(system_prompt, user_prompt)
            
            if response:
                # 后处理生成的评论
                comment = self._post_process_comment(response)
                self.logger.info(f"AI生成评论成功: {comment}")
                return comment
            
            return None
            
        except Exception as e:
            self.logger.error(f"AI生成评论失败: {e}")
            return None
    
    def _build_comment_prompt(self, tweet_data: Dict[str, Any]) -> tuple[str, str]:
        """构建评论生成的提示词，返回(system_prompt, user_prompt)"""
        content = tweet_data.get('content', '')
        username = tweet_data.get('username', '')
        like_count = tweet_data.get('like_count', '0')
        retweet_count = tweet_data.get('retweet_count', '0')
        is_verified = tweet_data.get('is_verified', False)
        
        # 检测内容语言
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in content)
        
        if is_chinese:
            # 中文提示词
            system_prompt = """
你是一个友好且精通社交媒体的助手，专门帮助用户创作真实的推特回复评论。当用户提供一条推文时，请生成一条**简短真诚的评论**，要求如下：

1.  **人性化与个性化**：
    → 用朋友闲聊般的自然口吻写作，避免机械感、陈词滥调或过度吹捧
    → 根据可用上下文，让回复隐约体现该用户的个人风格

2.  **匹配情绪与语境**：
    → 准确捕捉原推文的情感氛围（如兴奋/支持/思考/吐槽/搞笑）
    → 理解话题核心，确保评论内容相关

3.  **简洁有力**：
    → 长度通常控制在70字内（中文计字符），但以自然流畅为优先
    → 聚焦核心情绪传递，避免冗余信息

4.  **精准使用表情**：
    → 最多添加1-2个表情符号，且仅在能自然增强情感时使用
    → 禁止堆砌表情或强行添加

5.  **安全可信原则**：
    → 保持中立或积极立场
    → 严禁涉及政治、争议话题、广告营销及虚假内容
    → 只用中文撰写

6.  **纯净输出**：
    → 仅返回评论正文，无需格式、标号或解释说明
            """
            
            user_prompt = f"推文内容: {content}"
            
        else:
            # 英文提示词
            system_prompt = """
You are a friendly, social-media-savvy assistant that helps users craft authentic replies to tweets. When the user provides a tweet, generate a **short, genuine comment** that:

1.  **Feels Human & Personalized:** Write conversationally, like a real friend commenting. Avoid robotic phrasing, clichés, or exaggerated praise. Tailor the tone subtly to feel like it's coming from the specific user (based on context if available).
2.  **Matches Tone & Context:** Reflect the emotional vibe of the original tweet (e.g., excited, supportive, thoughtful, sarcastic, funny). Understand the topic to make the reply relevant.
3.  **Be Concise & Engaging:** Aim for brevity (typically under 100 characters for readability, but prioritize naturalness over strict limits). Focus on impact.
4.  **Use Emojis Tastefully:** Include 1-2 relevant emojis *only* if they genuinely enhance warmth or emotion. Don't force them.
5.  **Stay Safe & Sincere:** Be positive or neutral. Avoid anything controversial, political, promotional, or insincere. Write exclusively in English.
6.  **Output Only:** Provide **only** the reply comment text itself, with no additional explanation or formatting.
            """
            
            user_prompt = f"""Tweet author: @{username} {'(verified)' if is_verified else ''}
Tweet content: {content}
Engagement: {like_count} likes, {retweet_count} retweets"""
        
        return system_prompt, user_prompt
    
    async def _call_deepseek_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
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
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
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