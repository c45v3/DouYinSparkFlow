import re
import requests
from utils.logger import setup_logger

logger = setup_logger()


class NotificationService:
    """任务结束后推送执行结果。"""

    def __init__(self, config: dict):
        self.config = config

    def send(self, message: str):
        title = (self.config.get("notifyTitle") or "DouYin Spark Flow 任务结果").strip()

        bark_configured = bool(self.config.get("barkServerUrl") and self.config.get("barkDeviceKey"))
        server3_configured = bool(self.config.get("server3SendKey"))
        delivered = [
            self._send_bark(title, message),
            self._send_server3(title, message),
        ]

        if any(delivered):
            return True

        if bark_configured or server3_configured:
            logger.warning("通知渠道已配置，但本次推送均失败")
        else:
            logger.info("未配置通知渠道，已跳过结果推送")
        return False

    def _send_bark(self, title: str, message: str) -> bool:
        server = self.config.get("barkServerUrl")
        device_key = self.config.get("barkDeviceKey")
        if not server or not device_key:
            return False

        url = f"{server}/{device_key}/{title}/{message}"
        for attempt in range(1, 4):
            try:
                logger.info(f"Bark 推送中（第 {attempt}/3 次）")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return True
            except requests.RequestException as exc:
                logger.warning(f"Bark 推送失败（第 {attempt}/3 次）: {exc}")
        return False

    def _send_server3(self, title: str, message: str) -> bool:
        send_key = self.config.get("server3SendKey")
        if not send_key:
            return False

        api_url = self._build_server3_api_url(send_key)
        payload = {
            "title": title,
            "desp": message,
            "tags": "GitHub Action|DouYinSparkFlow",
        }

        for attempt in range(1, 4):
            try:
                logger.info(f"Server酱3 推送中（第 {attempt}/3 次）")
                response = requests.post(api_url, json=payload, timeout=10)
                data = response.json()

                if response.status_code == 200 and data.get("code") == 0:
                    return True

                logger.warning(
                    f"Server酱3 推送未成功（第 {attempt}/3 次）: status={response.status_code}, code={data.get('code')}"
                )
            except ValueError:
                logger.warning(f"Server酱3 返回非 JSON（第 {attempt}/3 次）")
            except requests.RequestException as exc:
                logger.warning(f"Server酱3 推送失败（第 {attempt}/3 次）: {exc}")
        return False

    def _build_server3_api_url(self, send_key: str) -> str:
        """
        官方格式：https://<uid>.push.ft07.com/send/<sendkey>.send
        兼容回退：https://sctapi.ftqq.com/<sendkey>.send
        """
        uid_match = re.search(r"^sctp(\d+)t", send_key)
        if uid_match:
            uid = uid_match.group(1)
            return f"https://{uid}.push.ft07.com/send/{send_key}.send"

        logger.warning("Server酱3 sendKey 未匹配到 uid，回退到兼容地址 sctapi.ftqq.com")
        return f"https://sctapi.ftqq.com/{send_key}.send"
