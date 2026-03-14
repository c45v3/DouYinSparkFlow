import requests
from datetime import date
from utils.config import get_config
from utils.hitokoto import request_hitokoto

def get_env_info():
    """从 api.ipapi.is 获取信息并脱敏 IP"""
    try:
        response = requests.get("https://api.ipapi.is/", timeout=8)
        data = response.json()
        
        raw_ip = data.get("ip", "未知IP")
        
        # --- 关键代码：隐藏 C 段 ---
        if "." in raw_ip:
            # 将 1.2.3.4 分割，保留前三段，最后一段替换为 *
            ip_parts = raw_ip.split(".")
            mask_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.*"
        elif ":" in raw_ip:
            # 如果是 IPv6，处理方式类似 (取前四组)
            ip_parts = raw_ip.split(":")
            mask_ip = f"{':'.join(ip_parts[:4])}:*:*:*:*"
        else:
            mask_ip = raw_ip
        # ------------------------

        country = data.get("location", {}).get("country", "未知国家")
        
        dc_info = data.get("datacenter", {}).get("datacenter")
        if not dc_info:
            dc_info = data.get("asn", {}).get("org", "非机房网络")
            
        return mask_ip, country, dc_info
    except Exception:
        return "查询失败", "未知国家", "获取失败"

def build_message() -> str:
    # ... (此处保持你之前的 build_message 逻辑不变) ...
    
    # 动态适配环境信息标签
    if any(tag in message for tag in ["[IP]", "[COUNTRY]", "[DC]"]):
        mask_ip, country_name, dc_name = get_env_info()
        message = message.replace("[IP]", mask_ip)
        message = message.replace("[COUNTRY]", country_name)
        message = message.replace("[DC]", dc_name)

    return message.strip()
