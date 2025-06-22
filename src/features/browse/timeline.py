"""
时间线浏览功能
"""
import asyncio
from typing import List, Dict, Any, Optional
from ...core.twitter.client import TwitterClient
from ...core.browser.manager import BrowserManager
from ...utils.logger import log
from ...utils.storage import storage

class TimelineBrowser:
    """时间线浏览器"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.twitter_client = None
    
    async def start_browsing(self, auto_interact: bool = False) -> List[Dict[str, Any]]:
        """开始浏览时间线"""
        try:
            if not self.twitter_client:
                self.twitter_client = TwitterClient(self.browser_manager.page)
            
            # 检查登录状态
            if not await self.twitter_client.check_login_status():
                log.info("需要登录，开始登录流程...")
                if not await self.twitter_client.login():
                    raise Exception("登录失败")
            
            # 获取时间线推文
            log.info("开始获取时间线推文...")
            tweets = await self.twitter_client.get_timeline_tweets(count=20)
            
            if not tweets:
                log.warning("未获取到推文")
                return []
            
            # 保存推文数据
            await self._save_tweets(tweets)
            
            # 如果启用自动互动
            if auto_interact:
                await self._auto_interact_with_tweets(tweets)
            
            return tweets
            
        except Exception as e:
            log.error(f"浏览时间线失败: {e}")
            return []
    
    async def _save_tweets(self, tweets: List[Dict[str, Any]]):
        """保存推文数据"""
        try:
            # 移除不能序列化的元素引用
            clean_tweets = []
            for tweet in tweets:
                clean_tweet = {k: v for k, v in tweet.items() if k != 'element'}
                clean_tweets.append(clean_tweet)
            
            # 保存到存储
            timestamp = int(asyncio.get_event_loop().time())
            filename = f"timeline_{timestamp}"
            
            storage.save_json(filename, {
                "tweets": clean_tweets,
                "count": len(clean_tweets),
                "timestamp": timestamp
            })
            
            log.info(f"已保存 {len(clean_tweets)} 条推文到 {filename}")
            
        except Exception as e:
            log.error(f"保存推文失败: {e}")
    
    async def _auto_interact_with_tweets(self, tweets: List[Dict[str, Any]]):
        """自动与推文互动"""
        try:
            log.info("开始自动互动...")
            
            for i, tweet in enumerate(tweets[:5]):  # 只与前5条推文互动
                try:
                    tweet_element = tweet.get('element')
                    if not tweet_element:
                        continue
                    
                    log.info(f"与推文 {i+1} 互动: {tweet['content'][:50]}...")
                    
                    # 随机延迟
                    await self.browser_manager.random_delay(1, 3)
                    
                    # 50%概率点赞
                    if asyncio.get_event_loop().time() % 2 < 1:
                        await self.twitter_client.like_tweet(tweet_element)
                        await self.browser_manager.random_delay(0.5, 1.5)
                    
                    # 20%概率转发
                    if asyncio.get_event_loop().time() % 5 < 1:
                        await self.twitter_client.retweet(tweet_element)
                        await self.browser_manager.random_delay(1, 2)
                    
                except Exception as e:
                    log.warning(f"与推文 {i+1} 互动失败: {e}")
                    continue
            
            log.info("自动互动完成")
            
        except Exception as e:
            log.error(f"自动互动失败: {e}")
    
    async def search_tweets(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """搜索推文"""
        try:
            if not self.twitter_client:
                self.twitter_client = TwitterClient(self.browser_manager.page)
            
            log.info(f"搜索推文: {query}")
            
            # 访问搜索页面
            search_url = f"https://twitter.com/search?q={query}&src=typed_query"
            await self.browser_manager.page.goto(search_url)
            await self.browser_manager.page.wait_for_load_state("networkidle")
            
            # 获取搜索结果
            tweets = await self.twitter_client.get_timeline_tweets(count=count)
            
            # 保存搜索结果
            if tweets:
                await self._save_search_results(query, tweets)
            
            return tweets
            
        except Exception as e:
            log.error(f"搜索推文失败: {e}")
            return []
    
    async def _save_search_results(self, query: str, tweets: List[Dict[str, Any]]):
        """保存搜索结果"""
        try:
            # 移除不能序列化的元素引用
            clean_tweets = []
            for tweet in tweets:
                clean_tweet = {k: v for k, v in tweet.items() if k != 'element'}
                clean_tweets.append(clean_tweet)
            
            timestamp = int(asyncio.get_event_loop().time())
            filename = f"search_{query.replace(' ', '_')}_{timestamp}"
            
            storage.save_json(filename, {
                "query": query,
                "tweets": clean_tweets,
                "count": len(clean_tweets),
                "timestamp": timestamp
            })
            
            log.info(f"已保存搜索结果到 {filename}")
            
        except Exception as e:
            log.error(f"保存搜索结果失败: {e}") 