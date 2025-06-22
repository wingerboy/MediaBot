"""
Twitter客户端
"""
import asyncio
from typing import Optional, List, Dict, Any
from playwright.async_api import Page
import re

from ...utils.logger import log
from ...utils.storage import storage
from config.settings import settings

class TwitterClient:
    """Twitter操作客户端"""
    
    def __init__(self, page: Page):
        self.page = page
        self.is_logged_in = False
    
    async def login(self, username: str = None, password: str = None, email: str = None) -> bool:
        """登录Twitter"""
        try:
            username = username or settings.TWITTER_USERNAME
            password = password or settings.TWITTER_PASSWORD
            email = email or settings.TWITTER_EMAIL
            
            if not username or not password:
                raise ValueError("用户名和密码不能为空")
            
            log.info("开始登录Twitter...")
            
            # 访问登录页面
            await self.page.goto("https://twitter.com/i/flow/login")
            await self.page.wait_for_load_state("networkidle")
            
            # 输入用户名
            username_input = self.page.locator('input[autocomplete="username"]')
            await username_input.wait_for(state="visible")
            await username_input.fill(username)
            
            # 点击下一步
            next_button = self.page.locator('div[role="button"]:has-text("Next")')
            await next_button.click()
            
            # 处理可能的邮箱验证
            try:
                email_input = self.page.locator('input[data-testid="ocfEnterTextTextInput"]')
                await email_input.wait_for(state="visible", timeout=3000)
                if email:
                    await email_input.fill(email)
                    next_button = self.page.locator('div[role="button"]:has-text("Next")')
                    await next_button.click()
            except:
                pass  # 如果没有邮箱验证步骤就跳过
            
            # 输入密码
            password_input = self.page.locator('input[name="password"]')
            await password_input.wait_for(state="visible")
            await password_input.fill(password)
            
            # 点击登录
            login_button = self.page.locator('div[role="button"]:has-text("Log in")')
            await login_button.click()
            
            # 等待登录完成
            await self.page.wait_for_url("https://twitter.com/home", timeout=30000)
            
            self.is_logged_in = True
            log.info("登录成功")
            
            return True
            
        except Exception as e:
            log.error(f"登录失败: {e}")
            return False
    
    async def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            # 检查是否在主页
            if "twitter.com/home" in self.page.url:
                self.is_logged_in = True
                return True
            
            # 尝试访问主页
            await self.page.goto("https://twitter.com/home")
            await self.page.wait_for_load_state("networkidle")
            
            # 如果被重定向到登录页面，说明没有登录
            if "login" in self.page.url:
                self.is_logged_in = False
                return False
            
            self.is_logged_in = True
            return True
            
        except Exception as e:
            log.error(f"检查登录状态失败: {e}")
            return False
    
    async def get_timeline_tweets(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取时间线推文"""
        try:
            if not self.is_logged_in:
                await self.check_login_status()
            
            if not self.is_logged_in:
                raise Exception("未登录")
            
            # 确保在主页
            await self.page.goto("https://twitter.com/home")
            await self.page.wait_for_load_state("networkidle")
            
            tweets = []
            
            # 多次尝试获取推文元素
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="tweet"]',
                'article[role="article"]',
                'div[aria-label*="timeline"] article'
            ]
            
            tweet_elements = []
            for selector in tweet_selectors:
                try:
                    elements = self.page.locator(selector)
                    element_count = await elements.count()
                    if element_count > 0:
                        tweet_elements = [elements.nth(i) for i in range(element_count)]
                        log.info(f"找到 {element_count} 个推文元素 (使用选择器: {selector})")
                        break
                except Exception as e:
                    log.debug(f"推文选择器失败 {selector}: {e}")
                    continue
            
            if not tweet_elements:
                log.warning("未找到推文元素")
                return tweets
            
            # 限制获取数量
            tweet_elements = tweet_elements[:count]
            
            for i, tweet_element in enumerate(tweet_elements):
                try:
                    # 提取推文信息
                    tweet_data = await self._extract_tweet_data(tweet_element)
                    if tweet_data:
                        tweets.append(tweet_data)
                        log.debug(f"已获取推文 {i+1}/{len(tweet_elements)}: {tweet_data.get('username', 'Unknown')} - {tweet_data.get('content', '')[:30]}...")
                except Exception as e:
                    log.warning(f"提取推文数据失败 (推文{i+1}): {e}")
                    continue
            
            log.info(f"成功获取 {len(tweets)} 条推文 (目标: {count})")
            return tweets
            
        except Exception as e:
            log.error(f"获取时间线推文失败: {e}")
            return []
    
    async def _extract_tweet_data(self, tweet_element) -> Optional[Dict[str, Any]]:
        """从推文元素提取数据"""
        try:
            # 基础推文信息
            tweet_data = {}
            
            # === 作者信息 ===
            author_info = await self._extract_author_info(tweet_element)
            tweet_data.update(author_info)
            
            # === 推文内容 ===
            content = await self._extract_tweet_content(tweet_element)
            
            # 确保内容不为空，否则跳过这条推文
            if not content or not content.strip():
                log.debug("推文内容为空，跳过")
                return None
            
            tweet_data["content"] = content.strip()
            
            # === 时间信息 ===
            time_str = await self._extract_tweet_time(tweet_element)
            tweet_data["time"] = time_str
            
            # === 推文链接 ===
            tweet_url = await self._extract_tweet_url(tweet_element)
            tweet_data["tweet_url"] = tweet_url
            tweet_data["tweet_id"] = self._extract_tweet_id_from_url(tweet_url)
            
            # === 互动数据 ===
            interaction_data = await self._extract_interaction_data(tweet_element)
            tweet_data.update(interaction_data)
            
            # === 媒体信息 ===
            media_info = await self._extract_media_info(tweet_element)
            tweet_data.update(media_info)
            
            # 保存元素引用
            tweet_data["element"] = tweet_element
            
            log.debug(f"成功提取推文: {tweet_data.get('username', 'Unknown')} - {content[:50]}...")
            return tweet_data
            
        except Exception as e:
            log.warning(f"提取推文数据失败: {e}")
            return None
    
    async def _extract_tweet_content(self, tweet_element) -> str:
        """提取推文内容，避免strict mode violation"""
        content = ""
        try:
            # 尝试多种方法获取推文内容
            content_selectors = [
                'div[data-testid="tweetText"]',
                '[data-testid="tweetText"]',
                'div[lang]',  # 备用：具有语言属性的div
            ]
            
            for selector in content_selectors:
                try:
                    content_elements = tweet_element.locator(selector)
                    count = await content_elements.count()
                    
                    if count > 0:
                        # 如果有多个元素，尝试获取每个并合并
                        all_texts = []
                        for i in range(count):
                            try:
                                element = content_elements.nth(i)
                                text = await element.text_content()
                                if text and text.strip():
                                    # 过滤掉可能是用户名或时间的短文本
                                    if len(text.strip()) > 5 and not text.strip().startswith('@'):
                                        all_texts.append(text.strip())
                            except Exception as e:
                                log.debug(f"获取第{i}个内容元素失败: {e}")
                                continue
                        
                        if all_texts:
                            # 选择最长的文本作为主要内容
                            content = max(all_texts, key=len)
                            if content:
                                break
                        
                except Exception as e:
                    log.debug(f"使用选择器 {selector} 失败: {e}")
                    continue
            
            # 如果仍然没有内容，尝试获取整个推文的文本并过滤
            if not content:
                try:
                    all_text = await tweet_element.text_content()
                    if all_text:
                        # 简单的内容提取：查找较长的文本行
                        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                        # 过滤掉用户名、时间等短文本
                        content_lines = [
                            line for line in lines 
                            if len(line) > 10 and not line.startswith('@') and 
                            not line.endswith('ago') and not 'h' in line and not 'm' in line
                        ]
                        if content_lines:
                            content = content_lines[0]  # 取第一个符合条件的文本
                except Exception as e:
                    log.debug(f"备用内容提取失败: {e}")
            
        except Exception as e:
            log.debug(f"提取推文内容失败: {e}")
        
        return content
    
    async def _extract_tweet_time(self, tweet_element) -> str:
        """提取推文时间"""
        try:
            time_element = tweet_element.locator('time')
            if await time_element.count() > 0:
                # 优先获取datetime属性
                datetime_attr = await time_element.first.get_attribute('datetime')
                if datetime_attr:
                    return datetime_attr
                
                # 如果没有datetime属性，获取文本内容
                time_text = await time_element.first.text_content()
                if time_text:
                    return time_text.strip()
                
        except Exception as e:
            log.debug(f"获取时间失败: {e}")
        
        return ""
    
    async def _extract_author_info(self, tweet_element) -> Dict[str, Any]:
        """提取作者信息"""
        author_info = {
            "username": "Unknown",
            "display_name": "Unknown", 
            "user_handle": "Unknown",
            "is_verified": False
        }
        
        try:
            # 用户名和显示名 - 使用更稳定的选择器
            user_name_selectors = [
                'div[data-testid="User-Name"]',
                '[data-testid="User-Name"]',
                'div[data-testid="User-Names"]'
            ]
            
            user_name_section = None
            for selector in user_name_selectors:
                try:
                    element = tweet_element.locator(selector)
                    if await element.count() > 0:
                        user_name_section = element.first
                        break
                except Exception as e:
                    log.debug(f"用户名选择器 {selector} 失败: {e}")
                    continue
            
            if user_name_section:
                # 显示名称 - 通常是第一个具有较大字体的文本
                try:
                    display_name_elements = user_name_section.locator('span')
                    count = await display_name_elements.count()
                    if count > 0:
                        for i in range(min(count, 3)):  # 最多检查前3个span
                            try:
                                display_name = await display_name_elements.nth(i).text_content()
                                if display_name and display_name.strip() and not display_name.startswith('@'):
                                    author_info["display_name"] = display_name.strip()
                                    break
                            except Exception as e:
                                log.debug(f"获取显示名失败 {i}: {e}")
                                continue
                except Exception as e:
                    log.debug(f"获取显示名失败: {e}")
                
                # 用户handle（@用户名）
                try:
                    # 查找包含@的文本
                    handle_selectors = [
                        'span:has-text("@")',
                        'a[href*="/"]',  # 用户链接
                        'span[dir="ltr"]'  # 通常用户名是ltr方向
                    ]
                    
                    for handle_selector in handle_selectors:
                        try:
                            handle_elements = user_name_section.locator(handle_selector)
                            count = await handle_elements.count()
                            if count > 0:
                                for i in range(count):
                                    try:
                                        handle_text = await handle_elements.nth(i).text_content()
                                        if handle_text and '@' in handle_text:
                                            handle = handle_text.strip()
                                            author_info["user_handle"] = handle
                                            # 去掉@符号作为username
                                            username = handle.replace("@", "").strip()
                                            if username:
                                                author_info["username"] = username
                                            break
                                    except Exception as e:
                                        log.debug(f"获取handle失败 {i}: {e}")
                                        continue
                                if author_info["username"] != "Unknown":
                                    break
                        except Exception as e:
                            log.debug(f"Handle选择器 {handle_selector} 失败: {e}")
                            continue
                except Exception as e:
                    log.debug(f"获取用户handle失败: {e}")
            
            # 验证标识
            try:
                verified_selectors = [
                    'svg[data-testid="icon-verified"]',
                    '[data-testid="icon-verified"]',
                    'svg[aria-label*="Verified"]'
                ]
                
                for verified_selector in verified_selectors:
                    try:
                        verified_element = tweet_element.locator(verified_selector)
                        if await verified_element.count() > 0:
                            author_info["is_verified"] = True
                            break
                    except Exception as e:
                        log.debug(f"验证选择器 {verified_selector} 失败: {e}")
                        continue
            except Exception as e:
                log.debug(f"获取验证状态失败: {e}")
            
            # 尝试从用户链接获取更准确的用户名
            try:
                link_selectors = [
                    'div[data-testid="User-Name"] a',
                    'a[href*="/"]'
                ]
                
                for link_selector in link_selectors:
                    try:
                        user_links = tweet_element.locator(link_selector)
                        count = await user_links.count()
                        if count > 0:
                            for i in range(count):
                                try:
                                    href = await user_links.nth(i).get_attribute('href')
                                    if href and href.startswith('/') and '/' in href[1:]:
                                        username_from_url = href.split('/')[1]
                                        if username_from_url and len(username_from_url) > 0:
                                            author_info["username"] = username_from_url
                                            author_info["profile_url"] = f"https://x.com{href}"
                                            if not author_info["user_handle"] or author_info["user_handle"] == "Unknown":
                                                author_info["user_handle"] = f"@{username_from_url}"
                                            break
                                except Exception as e:
                                    log.debug(f"获取用户链接失败 {i}: {e}")
                                    continue
                            if author_info["username"] != "Unknown":
                                break
                    except Exception as e:
                        log.debug(f"链接选择器 {link_selector} 失败: {e}")
                        continue
            except Exception as e:
                log.debug(f"获取用户链接失败: {e}")
            
        except Exception as e:
            log.debug(f"提取作者信息失败: {e}")
        
        return author_info
    
    async def _extract_tweet_url(self, tweet_element) -> str:
        """提取推文链接"""
        try:
            # 尝试多种方法找到推文链接
            link_strategies = [
                # 策略1: 通过时间元素的父级链接
                lambda: tweet_element.locator('time').locator('xpath=ancestor::a[1]'),
                # 策略2: 查找包含status的链接
                lambda: tweet_element.locator('a[href*="/status/"]'),
                # 策略3: 查找时间相关的链接
                lambda: tweet_element.locator('a').filter(has=tweet_element.locator('time')),
                # 策略4: 查找任何指向推文的链接
                lambda: tweet_element.locator('a[href*="twitter.com"], a[href*="x.com"]')
            ]
            
            for strategy in link_strategies:
                try:
                    link_elements = strategy()
                    count = await link_elements.count()
                    if count > 0:
                        for i in range(count):
                            try:
                                href = await link_elements.nth(i).get_attribute('href')
                                if href:
                                    # 标准化URL
                                    if href.startswith('/'):
                                        full_url = f"https://x.com{href}"
                                    elif href.startswith('http'):
                                        full_url = href
                                    else:
                                        continue
                                    
                                    # 验证是否是推文链接
                                    if '/status/' in full_url:
                                        return full_url
                            except Exception as e:
                                log.debug(f"获取链接href失败 {i}: {e}")
                                continue
                except Exception as e:
                    log.debug(f"链接策略失败: {e}")
                    continue
            
            return ""
            
        except Exception as e:
            log.debug(f"提取推文链接失败: {e}")
            return ""
    
    def _extract_tweet_id_from_url(self, url: str) -> str:
        """从URL中提取推文ID"""
        try:
            if "/status/" in url:
                # 提取status/后面的数字
                parts = url.split("/status/")
                if len(parts) > 1:
                    tweet_id = parts[1].split("?")[0].split("/")[0]  # 去掉查询参数和后续路径
                    return tweet_id
            return ""
        except Exception as e:
            log.debug(f"提取推文ID失败: {e}")
            return ""
    
    async def _extract_interaction_data(self, tweet_element) -> Dict[str, Any]:
        """提取互动数据 - 优先获取完整数字而非简化格式"""
        interaction_data = {
            "like_count": "0",
            "retweet_count": "0", 
            "reply_count": "0",
            "view_count": "0",
            "bookmark_count": "0"
        }
        
        try:
            # 优先策略：从aria-label获取完整的准确数字
            success = await self._extract_from_aria_labels(tweet_element, interaction_data)
            
            # 如果aria-label获取不完整，使用传统方法补充
            if not success:
                await self._extract_from_button_text(tweet_element, interaction_data)
            
            # 最后的备用方案：从role="group"解析
            missing_data = [k for k, v in interaction_data.items() if v == "0"]
            if missing_data:
                await self._extract_from_group_text(tweet_element, interaction_data)
                
        except Exception as e:
            log.debug(f"获取互动数据失败: {e}")
        
        return interaction_data
    
    async def _extract_from_aria_labels(self, tweet_element, interaction_data: Dict[str, Any]) -> bool:
        """从aria-label提取完整的准确数字"""
        try:
            # 查找包含完整互动信息的aria-label
            elements_with_labels = tweet_element.locator('[aria-label]')
            label_count = await elements_with_labels.count()
            
            for i in range(label_count):
                try:
                    element = elements_with_labels.nth(i)
                    aria_label = await element.get_attribute('aria-label')
                    if not aria_label:
                        continue
                    
                    label_lower = aria_label.lower()
                    
                    # 解析完整的aria-label (如: "22 replies, 1743 reposts, 33329 likes, 1047 bookmarks, 524299 views")
                    if ('repl' in label_lower and 'repost' in label_lower and 'like' in label_lower):
                        # 这是包含完整信息的aria-label
                        self._parse_complete_aria_label(aria_label, interaction_data)
                        break
                    
                    # 解析单个数据的aria-label
                    elif 'view' in label_lower and 'view' in aria_label:
                        # 视图数据 (如: "524299 views. View post analytics")
                        view_numbers = re.findall(r'(\d+(?:,\d+)*)', aria_label)
                        if view_numbers and interaction_data["view_count"] == "0":
                            # 选择最大的数字（通常是浏览量）
                            max_number = max(view_numbers, key=lambda x: int(x.replace(',', '')))
                            interaction_data["view_count"] = max_number.replace(',', '')
                    
                except Exception as e:
                    log.debug(f"处理aria-label失败 {i}: {e}")
                    continue
            
            # 检查是否成功获取了大部分数据
            non_zero_count = sum(1 for v in interaction_data.values() if v != "0")
            return non_zero_count >= 3  # 至少获取到3个数据才算成功
            
        except Exception as e:
            log.debug(f"从aria-label提取数据失败: {e}")
            return False
    
    def _parse_complete_aria_label(self, aria_label: str, interaction_data: Dict[str, Any]):
        """解析完整的aria-label信息"""
        try:
            # 使用正则表达式解析各种格式的数字
            patterns = {
                'reply_count': [r'(\d+(?:,\d+)*)\s+repl', r'(\d+(?:,\d+)*)\s+回复'],
                'retweet_count': [r'(\d+(?:,\d+)*)\s+repost', r'(\d+(?:,\d+)*)\s+转发', r'(\d+(?:,\d+)*)\s+share'],
                'like_count': [r'(\d+(?:,\d+)*)\s+like', r'(\d+(?:,\d+)*)\s+赞'],
                'bookmark_count': [r'(\d+(?:,\d+)*)\s+bookmark', r'(\d+(?:,\d+)*)\s+书签'],
                'view_count': [r'(\d+(?:,\d+)*)\s+view', r'(\d+(?:,\d+)*)\s+查看']
            }
            
            for data_key, pattern_list in patterns.items():
                if interaction_data[data_key] == "0":  # 只更新未获取的数据
                    for pattern in pattern_list:
                        matches = re.findall(pattern, aria_label, re.IGNORECASE)
                        if matches:
                            # 移除逗号，转换为纯数字
                            number = matches[0].replace(',', '')
                            interaction_data[data_key] = number
                            break
                            
        except Exception as e:
            log.debug(f"解析完整aria-label失败: {e}")
    
    async def _extract_from_button_text(self, tweet_element, interaction_data: Dict[str, Any]):
        """从按钮文本提取数据（备用方案）"""
        try:
            interaction_mappings = {
                "like_count": [
                    'div[data-testid="like"] span',
                    '[data-testid="like"] span',
                    'button[data-testid="like"] span'
                ],
                "retweet_count": [
                    'div[data-testid="retweet"] span',
                    '[data-testid="retweet"] span', 
                    'button[data-testid="retweet"] span'
                ],
                "reply_count": [
                    'div[data-testid="reply"] span',
                    '[data-testid="reply"] span',
                    'button[data-testid="reply"] span'
                ]
            }
            
            for data_key, selectors in interaction_mappings.items():
                if interaction_data[data_key] != "0":  # 如果已经有数据，跳过
                    continue
                    
                try:
                    for selector in selectors:
                        try:
                            elements = tweet_element.locator(selector)
                            element_count = await elements.count()
                            if element_count > 0:
                                for i in range(element_count):
                                    try:
                                        text = await elements.nth(i).text_content()
                                        if text and text.strip():
                                            # 将简化格式转换为完整数字
                                            number = self._convert_to_full_number(text.strip())
                                            if number != "0":
                                                interaction_data[data_key] = number
                                                break
                                    except Exception as e:
                                        log.debug(f"获取按钮文本失败 {data_key}[{i}]: {e}")
                                        continue
                                if interaction_data[data_key] != "0":
                                    break
                        except Exception as e:
                            log.debug(f"按钮选择器失败 {selector}: {e}")
                            continue
                except Exception as e:
                    log.debug(f"获取按钮数据失败 {data_key}: {e}")
                    
        except Exception as e:
            log.debug(f"从按钮文本提取数据失败: {e}")
    
    def _convert_to_full_number(self, text: str) -> str:
        """将简化格式转换为完整数字"""
        try:
            import re
            
            # 移除空格和特殊字符
            text = text.strip()
            
            # 检查是否包含单位
            if re.search(r'[KMBkmbT万千]', text):
                # 提取数字和单位
                match = re.match(r'(\d+(?:\.\d+)?)\s*([KMBkmbT万千])', text, re.IGNORECASE)
                if match:
                    number_str, unit = match.groups()
                    number = float(number_str)
                    
                    # 转换单位
                    unit_lower = unit.lower()
                    if unit_lower == 'k' or unit == '千':
                        return str(int(number * 1000))
                    elif unit_lower == 'm' or unit == '万':
                        return str(int(number * 10000 if unit == '万' else number * 1000000))
                    elif unit_lower == 'b':
                        return str(int(number * 1000000000))
                    elif unit_lower == 't':
                        return str(int(number * 1000000000000))
            
            # 如果没有单位，直接返回数字
            numbers = re.findall(r'\d+', text.replace(',', ''))
            if numbers:
                return numbers[0]
                
            return "0"
            
        except Exception as e:
            log.debug(f"转换数字格式失败: {e}")
            return "0"
    
    async def _extract_from_group_text(self, tweet_element, interaction_data: Dict[str, Any]):
        """从role=group文本提取数据（最后备用方案）"""
        try:
            groups = tweet_element.locator('div[role="group"]')
            group_count = await groups.count()
            
            for i in range(group_count):
                try:
                    group = groups.nth(i)
                    group_text = await group.text_content()
                    if group_text:
                        # 解析组文本中的数字
                        patterns = re.findall(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*(\w+)|(\w+)\s*(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)', group_text, re.IGNORECASE)
                        
                        for match in patterns:
                            if match[0] and match[1]:  # 数字在前
                                number, word = match[0], match[1].lower()
                            elif match[2] and match[3]:  # 数字在后
                                word, number = match[2].lower(), match[3]
                            else:
                                continue
                            
                            # 转换为完整数字
                            full_number = self._convert_to_full_number(number)
                            
                            # 匹配关键词并更新未获取的数据
                            if ('like' in word or '赞' in word) and interaction_data["like_count"] == "0":
                                interaction_data["like_count"] = full_number
                            elif ('share' in word or 'retweet' in word or '转发' in word) and interaction_data["retweet_count"] == "0":
                                interaction_data["retweet_count"] = full_number
                            elif ('repl' in word or '回复' in word) and interaction_data["reply_count"] == "0":
                                interaction_data["reply_count"] = full_number
                            elif ('view' in word or '查看' in word) and interaction_data["view_count"] == "0":
                                interaction_data["view_count"] = full_number
                                
                except Exception as e:
                    log.debug(f"处理group文本失败 {i}: {e}")
                    continue
                    
        except Exception as e:
            log.debug(f"从group文本提取数据失败: {e}")
    
    async def _extract_media_info(self, tweet_element) -> Dict[str, Any]:
        """提取媒体信息"""
        media_info = {
            "has_images": False,
            "has_video": False,
            "has_gif": False,
            "media_count": 0,
            "media_urls": []
        }
        
        try:
            # 检查图片 - 使用多种选择器
            image_selectors = [
                'img[src*="media"]',
                'img[src*="pbs.twimg.com"]',
                'div[data-testid="tweetPhoto"] img',
                'div[aria-label*="Image"] img'
            ]
            
            for img_selector in image_selectors:
                try:
                    image_elements = tweet_element.locator(img_selector)
                    count = await image_elements.count()
                    if count > 0:
                        media_info["has_images"] = True
                        media_info["media_count"] += count
                        
                        # 提取图片URL
                        for i in range(count):
                            try:
                                src = await image_elements.nth(i).get_attribute('src')
                                if src and ('media' in src or 'pbs.twimg.com' in src):
                                    media_info["media_urls"].append(src)
                            except Exception as e:
                                log.debug(f"获取图片URL失败 {i}: {e}")
                                continue
                        break
                except Exception as e:
                    log.debug(f"图片选择器失败 {img_selector}: {e}")
                    continue
            
            # 检查视频 - 使用多种选择器
            video_selectors = [
                'video',
                'div[data-testid="videoPlayer"]',
                'div[data-testid="videoComponent"]',
                'div[aria-label*="video"]'
            ]
            
            for video_selector in video_selectors:
                try:
                    video_elements = tweet_element.locator(video_selector)
                    count = await video_elements.count()
                    if count > 0:
                        media_info["has_video"] = True
                        media_info["media_count"] += count
                        break
                except Exception as e:
                    log.debug(f"视频选择器失败 {video_selector}: {e}")
                    continue
            
            # 检查GIF - 使用多种选择器
            gif_selectors = [
                'div[data-testid="gif"]',
                'video[poster*="gif"]',
                'img[src*="gif"]',
                'div[aria-label*="GIF"]'
            ]
            
            for gif_selector in gif_selectors:
                try:
                    gif_elements = tweet_element.locator(gif_selector)
                    count = await gif_elements.count()
                    if count > 0:
                        media_info["has_gif"] = True
                        media_info["media_count"] += count
                        break
                except Exception as e:
                    log.debug(f"GIF选择器失败 {gif_selector}: {e}")
                    continue
                
        except Exception as e:
            log.debug(f"获取媒体信息失败: {e}")
        
        return media_info
    
    async def get_user_profile_info(self, username: str) -> Dict[str, Any]:
        """获取用户详细资料信息"""
        user_info = {
            "username": username,
            "display_name": "Unknown",
            "bio": "",
            "follower_count": 0,
            "following_count": 0,
            "tweet_count": 0,
            "is_verified": False,
            "is_protected": False,
            "location": "",
            "website": "",
            "joined_date": "",
            "profile_image_url": "",
            "banner_image_url": ""
        }
        
        try:
            # 访问用户资料页面
            profile_url = f"https://x.com/{username}"
            log.info(f"正在获取用户资料: {profile_url}")
            
            await self.page.goto(profile_url)
            await self.page.wait_for_load_state("networkidle")
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 显示名称
            try:
                display_name_element = self.page.locator('div[data-testid="UserName"] span').first
                if await display_name_element.count() > 0:
                    display_name = await display_name_element.text_content()
                    if display_name:
                        user_info["display_name"] = display_name.strip()
            except Exception as e:
                log.debug(f"获取显示名称失败: {e}")
            
            # 个人简介
            try:
                bio_element = self.page.locator('div[data-testid="UserDescription"]')
                if await bio_element.count() > 0:
                    bio = await bio_element.text_content()
                    if bio:
                        user_info["bio"] = bio.strip()
            except Exception as e:
                log.debug(f"获取个人简介失败: {e}")
            
            # 关注数据
            try:
                # 关注数（following）
                following_link = self.page.locator('a[href*="/following"]').first
                if await following_link.count() > 0:
                    following_text = await following_link.text_content()
                    if following_text:
                        # 提取数字
                        following_match = re.search(r'([\d,]+)', following_text.replace(',', ''))
                        if following_match:
                            user_info["following_count"] = int(following_match.group(1))
                
                # 粉丝数（followers）
                followers_link = self.page.locator('a[href*="/verified_followers"], a[href*="/followers"]').first
                if await followers_link.count() > 0:
                    followers_text = await followers_link.text_content()
                    if followers_text:
                        # 提取数字
                        followers_match = re.search(r'([\d,]+)', followers_text.replace(',', ''))
                        if followers_match:
                            user_info["follower_count"] = int(followers_match.group(1))
            except Exception as e:
                log.debug(f"获取关注数据失败: {e}")
            
            # 验证标识
            try:
                verified_element = self.page.locator('svg[data-testid="icon-verified"]')
                user_info["is_verified"] = await verified_element.count() > 0
            except Exception as e:
                log.debug(f"获取验证状态失败: {e}")
            
            # 受保护账户
            try:
                protected_element = self.page.locator('svg[data-testid="icon-lock"]')
                user_info["is_protected"] = await protected_element.count() > 0
            except Exception as e:
                log.debug(f"获取保护状态失败: {e}")
            
            # 位置信息
            try:
                location_element = self.page.locator('span[data-testid="UserLocation"]')
                if await location_element.count() > 0:
                    location = await location_element.text_content()
                    if location:
                        user_info["location"] = location.strip()
            except Exception as e:
                log.debug(f"获取位置信息失败: {e}")
            
            # 网站链接
            try:
                website_element = self.page.locator('a[data-testid="UserUrl"]')
                if await website_element.count() > 0:
                    website = await website_element.get_attribute('href')
                    if website:
                        user_info["website"] = website
            except Exception as e:
                log.debug(f"获取网站链接失败: {e}")
            
            # 头像
            try:
                avatar_element = self.page.locator('div[data-testid="UserAvatar-Container-"] img').first
                if await avatar_element.count() > 0:
                    avatar_src = await avatar_element.get_attribute('src')
                    if avatar_src:
                        user_info["profile_image_url"] = avatar_src
            except Exception as e:
                log.debug(f"获取头像失败: {e}")
            
            log.info(f"成功获取用户资料: {username}")
            return user_info
            
        except Exception as e:
            log.error(f"获取用户资料失败 {username}: {e}")
            return user_info
    
    async def like_tweet(self, tweet_element) -> bool:
        """点赞推文"""
        try:
            like_button = tweet_element.locator('div[data-testid="like"]')
            
            # 检查是否已经点赞
            is_liked = await like_button.get_attribute('data-testid')
            if 'liked' in str(is_liked):
                log.info("推文已点赞")
                return True
            
            await like_button.click()
            log.info("点赞成功")
            return True
            
        except Exception as e:
            log.error(f"点赞失败: {e}")
            return False
    
    async def retweet(self, tweet_element) -> bool:
        """转发推文"""
        try:
            retweet_button = tweet_element.locator('div[data-testid="retweet"]')
            await retweet_button.click()
            
            # 点击确认转发
            confirm_button = self.page.locator('div[data-testid="retweetConfirm"]')
            await confirm_button.click()
            
            log.info("转发成功")
            return True
            
        except Exception as e:
            log.error(f"转发失败: {e}")
            return False
    
    async def reply_to_tweet(self, tweet_element, reply_text: str) -> bool:
        """回复推文"""
        try:
            reply_button = tweet_element.locator('div[data-testid="reply"]')
            await reply_button.click()
            
            # 输入回复内容
            reply_input = self.page.locator('div[data-testid="tweetTextarea_0"]')
            await reply_input.wait_for(state="visible")
            await reply_input.fill(reply_text)
            
            # 发送回复
            send_button = self.page.locator('div[data-testid="tweetButtonInline"]')
            await send_button.click()
            
            log.info("回复成功")
            return True
            
        except Exception as e:
            log.error(f"回复失败: {e}")
            return False 