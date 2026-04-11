import requests
from utils.logger import setup_logger

logger = setup_logger()


class NotificationService:
    """任务结束后推送执行结果。"""

    def __init__(self, config: dict):
        self.config = config

    def send(self, message: str):
        title = self.config.get("notifyTitle", "DouYin Spark Flow 任务结果")
        delivered = [
            self._send_bark(title, message),
            self._send_server3(title, message),
        ]
        if not any(delivered):
            logger.info("未配置通知渠道，已跳过结果推送")

    def _send_bark(self, title: str, message: str) -> bool:
        server = self.config.get("barkServerUrl")
        device_key = self.config.get("barkDeviceKey")
        if not server or not device_key:
            return False

        try:
            url = f"{server}/{device_key}/{title}/{message}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            logger.info("Bark 推送成功")
        except requests.RequestException as exc:
            logger.warning(f"Bark 推送失败: {exc}")
        return True

    def _send_server3(self, title: str, message: str) -> bool:
        send_key = self.config.get("server3SendKey")
        if not send_key:
            return False

        try:
            response = requests.post(
                f"https://sctapi.ftqq.com/{send_key}.send",
                data={
                    "title": title,
                    "desp": message,
                    "tags": "GitHub Action,DouYinSparkFlow",
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Server酱3 推送成功")
        except requests.RequestException as exc:
            logger.warning(f"Server酱3 推送失败: {exc}")
        return True
