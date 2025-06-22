#!/usr/bin/env python3
"""
AutoX - 可配置的Twitter自动化任务系统
"""
import asyncio
import sys
import argparse
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.core.browser.manager import BrowserManager
from src.core.twitter.client import TwitterClient
from src.features.browse.timeline import TimelineBrowser
from src.features.actions.executor import ActionExecutor, ContentFilter
from src.config.task_config import SessionConfig, config_manager, ActionType
from src.utils.session_logger import get_session_logger, SessionLogger
from src.utils.session_data import SessionDataManager, ActionResult
from config.settings import settings

class AutoXSession:
    """AutoX自动化会话"""
    
    def __init__(self, session_config: SessionConfig, search_keywords: Optional[List[str]] = None):
        self.config = session_config
        self.session_id = session_config.session_id
        self.search_keywords = search_keywords or []
        
        # 初始化组件
        self.logger = get_session_logger(self.session_id)
        self.data_manager = SessionDataManager(self.session_id)
        self.browser_manager = None
        self.twitter_client = None
        self.timeline_browser = None
        self.action_executor = None
        self.content_filter = None
        
        # 会话状态
        self.start_time = datetime.now()
        self.action_counts = {action_type.value: 0 for action_type in ActionType}
        self.total_actions = 0
        self.is_running = False
    
    async def start(self):
        """启动会话"""
        try:
            self.logger.info(f"=== AutoX Session Starting ===")
            self.logger.info(f"Session ID: {self.session_id}")
            self.logger.info(f"Task Name: {self.config.name}")
            self.logger.info(f"Description: {self.config.description}")
            
            # 启动浏览器
            self.browser_manager = BrowserManager()
            await self.browser_manager.start()
            
            # 初始化客户端
            self.twitter_client = TwitterClient(self.browser_manager.page)
            self.timeline_browser = TimelineBrowser(self.browser_manager)
            self.action_executor = ActionExecutor(self.browser_manager.page, self.session_id)
            self.content_filter = ContentFilter(self.session_id)
            
            self.is_running = True
            self.logger.info("Session components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            await self.close()
            raise
    
    async def run_task(self):
        """执行主要任务"""
        try:
            # 检查登录状态
            if not await self.twitter_client.check_login_status():
                self.logger.info("Need to login, starting login process...")
                # 这里可以选择自动登录或提示手动登录
                login_success = await self.twitter_client.login(
                    username=settings.TWITTER_USERNAME,
                    password=settings.TWITTER_PASSWORD,
                    email=settings.TWITTER_EMAIL
                )
                if not login_success:
                    self.logger.error("Login failed, cannot continue")
                    return
            
            # 开始执行配置的任务
            await self._execute_configured_actions()
            
        except Exception as e:
            self.logger.error(f"Error during task execution: {e}")
        finally:
            await self.close()
    
    async def _execute_configured_actions(self):
        """执行配置的行为"""
        self.logger.info("Starting configured actions execution")
        
        # 计算总的时间限制
        max_end_time = self.start_time + timedelta(minutes=self.config.max_duration_minutes)
        
        for action_config in self.config.actions:
            if not action_config.enabled:
                self.logger.info(f"Skipping disabled action: {action_config.action_type.value}")
                continue
            
            await self._execute_single_action_type(action_config, max_end_time)
            
            # 检查是否超过总行为限制
            if self.total_actions >= self.config.max_total_actions:
                self.logger.info(f"Reached maximum total actions limit: {self.config.max_total_actions}")
                break
            
            # 检查时间限制
            if datetime.now() >= max_end_time:
                self.logger.info("Reached maximum session duration")
                break
    
    async def _execute_single_action_type(self, action_config, max_end_time):
        """执行单一类型的行为"""
        action_type = action_config.action_type
        target_count = action_config.count
        
        self.logger.info(f"Executing {action_type.value} actions (target: {target_count})")
        
        # 获取内容源
        try:
            content_source = await self._get_content_source()
        except Exception as e:
            self.logger.error(f"Error getting content source: {e}")
            return
        
        executed_count = 0
        processed_items = set()  # 防止重复处理
        
        while (executed_count < target_count and 
               self.total_actions < self.config.max_total_actions and
               datetime.now() < max_end_time):
            
            try:
                # 检查是否应该继续
                if not self.is_running:
                    break
                
                # 获取内容项
                content_items = await self._get_content_items(content_source, action_type)
                
                if not content_items:
                    self.logger.warning(f"No content items found for {action_type.value}")
                    break
                
                # 处理每个内容项
                for item in content_items:
                    # 再次检查运行状态和限制
                    if (executed_count >= target_count or 
                        self.total_actions >= self.config.max_total_actions or
                        datetime.now() >= max_end_time or
                        not self.is_running):
                        break
                    
                    item_id = item.get('id') or item.get('url', str(hash(str(item))))
                    if item_id in processed_items:
                        continue
                    
                    processed_items.add(item_id)
                    
                    # 内容过滤
                    try:
                        if not self.content_filter.should_interact(item, self.config.target):
                            continue
                    except Exception as e:
                        self.logger.debug(f"Error in content filter: {e}")
                        continue
                    
                    # 执行行为
                    try:
                        result = await self._execute_action_on_item(action_config, item)
                        
                        if result == ActionResult.SUCCESS:
                            executed_count += 1
                            self.action_counts[action_type.value] += 1
                            self.total_actions += 1
                        
                        # 记录行为
                        # 创建可序列化的details（排除Locator对象）
                        serializable_details = {
                            key: value for key, value in item.items() 
                            if key != 'element'  # 排除Locator对象
                        }
                        
                        self.data_manager.record_action(
                            action_type=action_type.value,
                            target_type="tweet" if action_type in [ActionType.LIKE, ActionType.RETWEET, ActionType.COMMENT] else "user",
                            target_id=item_id,
                            result=result,
                            details=serializable_details
                        )
                        
                    except Exception as e:
                        self.logger.error(f"Error executing action on item {item_id}: {e}")
                        continue
                    
                    # 行为间隔
                    try:
                        if self.config.randomize_intervals:
                            await self.action_executor.random_delay(
                                action_config.min_interval,
                                action_config.max_interval
                            )
                        else:
                            await asyncio.sleep(action_config.min_interval)
                    except asyncio.CancelledError:
                        self.logger.info("Action execution cancelled")
                        return
                    except Exception as e:
                        self.logger.debug(f"Error in delay: {e}")
                
                # 如果需要更多内容，滚动页面
                if (executed_count < target_count and 
                    self.total_actions < self.config.max_total_actions and
                    datetime.now() < max_end_time and
                    self.is_running):
                    try:
                        await self._scroll_for_more_content()
                        await asyncio.sleep(2)  # 等待内容加载
                    except asyncio.CancelledError:
                        self.logger.info("Scrolling cancelled")
                        return
                    except Exception as e:
                        self.logger.debug(f"Error scrolling: {e}")
                
            except asyncio.CancelledError:
                self.logger.info(f"Action execution for {action_type.value} was cancelled")
                return
            except Exception as e:
                self.logger.error(f"Error in action execution loop: {e}")
                break
        
        self.logger.info(f"Completed {action_type.value}: {executed_count}/{target_count} actions")
    
    async def _get_content_source(self):
        """获取内容源"""
        # 如果有搜索关键词，使用搜索；否则使用时间线
        if self.search_keywords:
            # 选择一个关键词进行搜索
            import random
            keyword = random.choice(self.search_keywords)
            self.logger.info(f"Using search results for keyword: {keyword}")
            await self.browser_manager.page.goto(f"https://x.com/search?q={keyword}")
        elif self.config.target.keywords:
            # 使用配置的关键词
            keyword = random.choice(self.config.target.keywords)
            self.logger.info(f"Using configured keyword: {keyword}")
            await self.browser_manager.page.goto(f"https://x.com/search?q={keyword}")
        else:
            # 使用主页时间线
            self.logger.info("Using home timeline")
            await self.browser_manager.page.goto("https://x.com/home")
        
        await self.browser_manager.page.wait_for_load_state("networkidle")
        return "timeline"
    
    async def _get_content_items(self, source_type: str, action_type: ActionType) -> List[Dict[str, Any]]:
        """获取内容项"""
        try:
            if action_type == ActionType.FOLLOW:
                # 对于关注行为，需要获取用户信息
                return await self._extract_users_from_page()
            else:
                # 对于其他行为，获取推文
                return await self._extract_tweets_from_page()
        except Exception as e:
            self.logger.error(f"Error getting content items: {e}")
            return []
    
    async def _extract_tweets_from_page(self) -> List[Dict[str, Any]]:
        """从页面提取推文信息"""
        tweets = []
        try:
            tweet_elements = await self.browser_manager.page.locator('article[data-testid="tweet"]').all()
            
            for i, tweet_element in enumerate(tweet_elements[:10]):  # 限制数量
                try:
                    tweet_data = await self.twitter_client._extract_tweet_data(tweet_element)
                    if tweet_data:
                        tweet_data['element'] = tweet_element
                        tweet_data['id'] = f"tweet_{i}_{hash(tweet_data.get('content', ''))}"
                        tweets.append(tweet_data)
                        
                        # 创建可序列化的数据副本（排除Locator对象）
                        serializable_data = {
                            key: value for key, value in tweet_data.items() 
                            if key != 'element'  # 排除Locator对象
                        }
                        
                        # 记录发现的目标
                        self.data_manager.record_target("tweet", tweet_data['id'], serializable_data)
                except Exception as e:
                    self.logger.debug(f"Error extracting tweet {i}: {e}")
                    continue
            
            self.logger.debug(f"Extracted {len(tweets)} tweets from page")
            return tweets
            
        except Exception as e:
            self.logger.error(f"Error extracting tweets: {e}")
            return []
    
    async def _extract_users_from_page(self) -> List[Dict[str, Any]]:
        """从页面提取用户信息"""
        users = []
        try:
            # 查找用户头像或用户名链接
            user_elements = await self.browser_manager.page.locator('div[data-testid="User-Names"]').all()
            
            for i, user_element in enumerate(user_elements[:5]):  # 限制数量
                try:
                    username_element = user_element.locator('span').first
                    username = await username_element.text_content()
                    
                    if username:
                        user_data = {
                            'username': username.strip(),
                            'element': user_element,
                            'id': f"user_{username.strip()}"
                        }
                        users.append(user_data)
                        
                        # 创建可序列化的数据副本（排除Locator对象）
                        serializable_data = {
                            key: value for key, value in user_data.items() 
                            if key != 'element'  # 排除Locator对象
                        }
                        
                        # 记录发现的目标
                        self.data_manager.record_target("user", user_data['id'], serializable_data)
                        
                except Exception as e:
                    self.logger.debug(f"Error extracting user {i}: {e}")
                    continue
            
            self.logger.debug(f"Extracted {len(users)} users from page")
            return users
            
        except Exception as e:
            self.logger.error(f"Error extracting users: {e}")
            return []
    
    async def _execute_action_on_item(self, action_config, item) -> ActionResult:
        """在项目上执行行为"""
        try:
            element = item.get('element')
            if not element:
                return ActionResult.ERROR
            
            result = await self.action_executor.execute_action(action_config, element, item)
            
            if result == ActionResult.SUCCESS:
                self.logger.info(f"Successfully executed {action_config.action_type.value} on {item.get('id', 'unknown')}")
            elif result == ActionResult.SKIPPED:
                self.logger.debug(f"Skipped {action_config.action_type.value} on {item.get('id', 'unknown')}")
            else:
                self.logger.warning(f"Failed {action_config.action_type.value} on {item.get('id', 'unknown')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing action: {e}")
            return ActionResult.ERROR
    
    async def _scroll_for_more_content(self):
        """滚动页面获取更多内容"""
        try:
            await self.browser_manager.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
        except Exception as e:
            self.logger.debug(f"Error scrolling: {e}")
    
    async def close(self):
        """关闭会话"""
        try:
            if self.is_running:
                self.logger.info("=== Session Closing ===")
                
                # 生成会话摘要
                try:
                    summary = self.data_manager.get_action_summary()
                    self.logger.info(f"Session Summary:")
                    self.logger.info(f"  Total Actions: {summary['total_actions']}")
                    self.logger.info(f"  Success Rate: {summary['success_rate']:.2%}")
                    self.logger.info(f"  Actions by Type: {summary['actions_by_type']}")
                except Exception as e:
                    self.logger.warning(f"Error generating session summary: {e}")
                
                # 关闭数据管理器
                try:
                    self.data_manager.close_session()
                except Exception as e:
                    self.logger.warning(f"Error closing data manager: {e}")
                
                # 关闭浏览器
                try:
                    if self.browser_manager:
                        await self.browser_manager.close()
                except Exception as e:
                    self.logger.warning(f"Error closing browser: {e}")
                
                self.is_running = False
                self.logger.info("=== Session Closed ===")
                
                # 关闭会话logger（放在最后）
                try:
                    SessionLogger.close_session_logger(self.session_id)
                except Exception as e:
                    print(f"Warning: Error closing session logger: {e}")
                
        except Exception as e:
            print(f"Error closing session: {e}")
            # 确保浏览器关闭
            try:
                if self.browser_manager:
                    await self.browser_manager.close()
            except:
                pass
            # 确保logger关闭
            try:
                SessionLogger.close_session_logger(self.session_id)
            except:
                pass

def create_sample_config(session_id: str, name: str) -> SessionConfig:
    """创建示例配置"""
    return config_manager.create_default_config(session_id, name)

def list_available_configs():
    """列出可用配置"""
    configs = config_manager.list_configs()
    if configs:
        print("Available task configurations:")
        for i, config_id in enumerate(configs, 1):
            print(f"  {i}. {config_id}")
    else:
        print("No saved configurations found.")
    return configs

async def run_session(session_config: SessionConfig, search_keywords: Optional[List[str]] = None):
    """运行会话"""
    session = AutoXSession(session_config, search_keywords)
    try:
        await session.start()
        await session.run_task()
    except KeyboardInterrupt:
        print(f"\n[{session_config.session_id}] Session interrupted by user")
        try:
            session.logger.info("Session interrupted by user (Ctrl+C)")
        except:
            pass
    except Exception as e:
        print(f"[{session_config.session_id}] Session error: {e}")
        try:
            session.logger.error(f"Session error: {e}")
        except:
            pass
    finally:
        # 确保会话正确关闭
        try:
            await session.close()
        except Exception as e:
            print(f"[{session_config.session_id}] Error during session cleanup: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AutoX - 可配置的Twitter自动化任务系统")
    parser.add_argument("--config", help="配置文件ID或路径")
    parser.add_argument("--name", default="AutoX Task", help="任务名称")
    parser.add_argument("--search", nargs="+", help="搜索关键词限制")
    parser.add_argument("--create-config", action="store_true", help="创建示例配置")
    parser.add_argument("--list-configs", action="store_true", help="列出可用配置")
    parser.add_argument("--session-id", help="自定义会话ID")
    
    args = parser.parse_args()
    
    # 检查环境变量
    if not any([settings.TWITTER_USERNAME, settings.TWITTER_PASSWORD]):
        print("Warning: Twitter credentials not configured in .env file")
    
    if args.list_configs:
        list_available_configs()
        return
    
    # 生成会话ID
    session_id = args.session_id or f"autox_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    if args.create_config:
        # 创建示例配置
        config = create_sample_config(session_id, args.name)
        config_path = config_manager.save_config(config)
        print(f"Sample configuration created: {config_path}")
        print(f"Edit the configuration file and run again with --config {session_id}")
        return
    
    # 加载配置
    if args.config:
        if Path(args.config).exists():
            # 从文件路径加载
            config = SessionConfig.load_from_file(Path(args.config))
        else:
            # 从ID加载
            config = config_manager.load_config(args.config)
        
        if not config:
            print(f"Configuration not found: {args.config}")
            return
    else:
        # 使用默认配置
        config = create_sample_config(session_id, args.name)
        print("Using default configuration (created on-the-fly)")
    
    # 更新会话ID
    config.session_id = session_id
    
    # 运行会话
    print(f"Starting AutoX session: {session_id}")
    print(f"Task: {config.name}")
    if args.search:
        print(f"Search keywords: {args.search}")
    
    asyncio.run(run_session(config, args.search))

if __name__ == "__main__":
    main() 