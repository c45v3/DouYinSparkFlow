import asyncio
import traceback
import logging
import time
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from utils.logger import setup_logger
from utils.config import get_config, get_userData
from core.msg_builder import build_message
from core.browser import get_browser

# 简单的脱敏工具函数
def mask_text(text):
    if not text or len(text) < 2: return "***"
    return f"{text[:1]}***"

config = get_config()
userData = get_userData()
logger = setup_logger(level=logging.DEBUG)

async def retry_operation(name, operation, retries=3, delay=2, *args, **kwargs):
    for attempt in range(retries):
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"{name} 失败，正在重试第 {attempt + 1} 次")
                await asyncio.sleep(delay)
            else:
                logger.error(f"{name} 失败，已达到最大重试次数")
                raise

async def scroll_and_select_user(page, username, targets):
    # 选择器根据抖音最新页面结构调整
    friends_tab_selector = 'xpath=//div[contains(text(), "好友")] | //*[@id="sub-app"]/div/div/div[1]/div[2]'
    target_selector = 'xpath=//div[contains(@class, "semi-list-item-body")]'
    
    logger.debug(f"账号 [{mask_text(username)}] 开始查找目标好友列表")

    try:
        await page.wait_for_selector(friends_tab_selector, timeout=10000)
        await page.locator(friends_tab_selector).click()
        await asyncio.sleep(2)
    except:
        logger.warning(f"无法点击好友标签，可能已在列表中")

    found_usernames = set()
    remaining_targets = set(targets)

    # 简化的滚动逻辑
    for _ in range(15): # 最多滚动 15 次
        target_elements = await page.locator(target_selector).all()
        for element in target_elements:
            try:
                targetName = await element.inner_text()
                # 匹配 targets 中的名字
                for t in remaining_targets:
                    if t in targetName:
                        await element.click()
                        logger.info(f"账号 [{mask_text(username)}] 选中目标好友 [{mask_text(t)}]")
                        yield t
                        remaining_targets.remove(t)
                        if not remaining_targets: return
                        break
            except: continue
        
        # 滚动翻页
        await page.mouse.wheel(0, 800)
        await asyncio.sleep(1)

async def do_user_task(browser, username, cookies, targets, semaphore):
    async with semaphore:
        context = await browser.new_context()
        context.set_default_timeout(30000) # 设置为 30 秒，避免死等

        page = await context.new_page()
        try:
            # 注入 Cookie 并直接访问聊天页
            await context.add_cookies(cookies)
            await page.goto("https://creator.douyin.com/creator-micro/data/following/chat", wait_until="networkidle")
            
            logger.info(f"账号 [{mask_text(username)}] 正在处理，当前 URL: {page.url}")

            async for target_user in scroll_and_select_user(page, username, targets):
                # 模糊匹配输入框类名，去掉末尾随机后缀
                chat_input_selector = "xpath=//div[contains(@class, 'chat-input-')]"
                
                try:
                    await page.wait_for_selector(chat_input_selector, timeout=15000)
                    chat_input = page.locator(chat_input_selector)

                    message = build_message()
                    lines = message.split("\n")
                    for i, line in enumerate(lines):
                        await chat_input.type(line)
                        if i < len(lines) - 1:
                            await chat_input.press("Shift+Enter")

                    await chat_input.press("Enter")
                    logger.info(f"账号 [{mask_text(username)}] 给好友 [{mask_text(target_user)}] 发送成功")
                    await asyncio.sleep(2)

                except PlaywrightTimeoutError:
                    # 截图保存，文件名包含用户名和时间戳
                    img_path = f"error_{username}_{int(time.time())}.png"
                    await page.screenshot(path=img_path, full_page=True)
                    logger.error(f"❌ 找不到输入框，截图已保存: {img_path}")
                    break 

        except Exception as e:
            logger.error(f"⚠️ 账号 [{mask_text(username)}] 异常: {str(e)}")
        finally:
            await context.close()

async def runTasks():
    playwright, browser = await get_browser()
    try:
        semaphore = asyncio.Semaphore(config["taskCount"] if config["multiTask"] else 1)
        tasks = []
        for user in userData:
            acc_name = user.get("username", "未知用户")
            tasks.append(do_user_task(browser, acc_name, user["cookies"], user["targets"], semaphore))

        await asyncio.gather(*tasks)
    finally:
        await browser.close()
        await playwright.stop()