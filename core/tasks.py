import asyncio
import traceback
import logging
from utils.logger import setup_logger
from utils.config import get_config, get_userData
from core.msg_builder import build_message
from core.browser import get_browser

# 简单的脱敏工具函数
def mask_text(text):
    if not text or len(text) < 2: return "***"
    return f"{text[:1]}***"

complates = {}

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
    friends_tab_selector = 'xpath=//*[@id="sub-app"]/div/div/div[1]/div[2]'
    target_selector = 'xpath=//*[@id="sub-app"]/div/div[1]/div[2]/div[2]//div[contains(@class, "semi-list-item-body semi-list-item-body-flex-start")]'
    scrollable_friends_selector = 'xpath=//*[@id="sub-app"]/div/div[1]/div[2]/div[2]/div/div/div[3]/div/div/div/ul/div'
    
    no_more_selector = 'xpath=//div[contains(@class, "no-more-tip-ftdJnu")]'
    loading_selector = 'xpath=//div[contains(@class, "semi-spin")]'

    logger.debug(f"账号 [{mask_text(username)}] 开始查找目标好友列表")

    await page.wait_for_selector(friends_tab_selector)
    await page.locator(friends_tab_selector).click()

    first_friend_selector = 'xpath=//*[@id="sub-app"]/div/div/div[2]/div[2]/div/div/div[1]/div/div/div/ul/div/div/div[1]/li/div'
    await page.wait_for_selector(first_friend_selector)
    await page.locator(first_friend_selector).click()

    await asyncio.sleep(2)

    found_usernames = set()
    remaining_targets = set(targets)

    while True:
        target_elements = await page.locator(target_selector).all()

        for element in target_elements:
            try:
                span = element.locator("""xpath=.//span[contains(@class, "item-header-name-")]""")
                targetName = await span.inner_text()

                if targetName in found_usernames:
                    continue
                found_usernames.add(targetName)

                if targetName in targets:
                    await element.click()
                    logger.info(f"账号 [{mask_text(username)}] 选中目标好友 [{mask_text(targetName)}]")
                    yield targetName
                    
                    if targetName in remaining_targets:
                        remaining_targets.remove(targetName)
                    if len(remaining_targets) == 0:
                        return
                    break
            except Exception:
                pass
        else:
            if await page.locator(no_more_selector).count() > 0:
                logger.info(f"账号 [{mask_text(username)}] 列表已到达底部")
                break

            if await page.locator(loading_selector).count() > 0:
                await asyncio.sleep(1.5)

            scrollable_element = await page.locator(scrollable_friends_selector).element_handle()
            if scrollable_element:
                await page.evaluate("(element) => element.scrollTop += 800", scrollable_element)
                await asyncio.sleep(1.5)
            else:
                break

async def do_user_task(browser, username, cookies, targets, semaphore):
    async with semaphore:
        context = await browser.new_context()
        context.set_default_navigation_timeout(120000)
        context.set_default_timeout(120000)

        page = await context.new_page()
        await retry_operation("进入中心", page.goto, url="https://creator.douyin.com/")
        await context.add_cookies(cookies)

        await retry_operation("进入消息", page.goto, url="https://creator.douyin.com/creator-micro/data/following/chat")
        
        logger.info(f"账号 [{mask_text(username)}] 开始发送消息")
        
        async for target_user in scroll_and_select_user(page, username, targets):
            chat_input_selector = "xpath=//div[contains(@class, 'chat-input-dccKiL')]"
            await page.wait_for_selector(chat_input_selector)
            chat_input = page.locator(chat_input_selector)

            message = build_message()
            for line in message.split("\n"):
                await chat_input.type(line)
                if line != message.split("\n")[-1]:
                    await chat_input.press("Shift+Enter")

            logger.info(f"账号 [{mask_text(username)}] 给好友 [{mask_text(target_user)}] 发送成功")
            await chat_input.press("Enter")
            await asyncio.sleep(2)

        await context.close()

async def runTasks():
    playwright, browser = await get_browser()
    try:
        logger.info(f"开始执行任务 | 多任务: {config['multiTask']} | 限制: {config['taskCount']}")
        
        semaphore = asyncio.Semaphore(config["taskCount"] if config["multiTask"] else 1)
        tasks = []
        for user in userData:
            cookies = user["cookies"]
            targets = user["targets"]
            complates[user["unique_id"]] = []
            acc_name = user.get("username", "未知用户")
            tasks.append(do_user_task(browser, acc_name, cookies, targets, semaphore))

        await asyncio.gather(*tasks)
    finally:
        await playwright.stop()
        await browser.close()
