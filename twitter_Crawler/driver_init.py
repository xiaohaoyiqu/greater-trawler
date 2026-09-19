import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ChromeOptions


def short_error(error):
    message = str(error).strip().splitlines()
    if message:
        return message[0]
    return error.__class__.__name__


def normalize_cookie_for_selenium(cookie):
    cookie = cookie.copy()

    if isinstance(cookie.get("expiry"), float):
        cookie["expiry"] = int(cookie["expiry"])

    if "expirationDate" in cookie and "expiry" not in cookie:
        try:
            cookie["expiry"] = int(float(cookie.pop("expirationDate")))
        except (TypeError, ValueError):
            cookie.pop("expirationDate", None)

    same_site = cookie.get("sameSite")
    if same_site:
        same_site = str(same_site).strip().lower()
        same_site_map = {
            "lax": "Lax",
            "strict": "Strict",
            "none": "None",
            "no_restriction": "None",
            "unspecified": None,
        }
        same_site = same_site_map.get(same_site)
        if same_site:
            cookie["sameSite"] = same_site
        else:
            cookie.pop("sameSite", None)

    for unsupported_key in ("hostOnly", "session", "storeId", "id"):
        cookie.pop(unsupported_key, None)

    return cookie


def initialize_driver():
    # 初始化Chrome浏览器驱动
    options = ChromeOptions()
    options.set_capability(
        "goog:loggingPrefs", {"performance": "ALL"}
    )
    # # 启用无头浏览器模式
    # options.add_argument("--headless")
    # options.add_argument("--disable-gpu")  # 禁用GPU加速
    # options.add_argument("--window-size=1920x1080")  # 设置窗口大小，防止某些元素不可见

    # 1. 忽略SSL证书错误（解决handshake failed; SSL error code 1）
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    # -------------------------- 防检测配置（避免Twitter反爬） --------------------------
    options.add_argument('--no-sandbox')  # 禁用沙箱模式
    options.add_argument('--disable-dev-shm-usage')  # 解决/dev/shm内存不足
    options.add_argument('--disable-blink-features=AutomationControlled')  # 隐藏自动化标识
    options.add_experimental_option('useAutomationExtension', False)  # 禁用自动化扩展

    # 不启用无头模式时开启，调式代码或者看报错的时候使用。
    options.add_argument("window-position=660,0")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-logging")
    options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])  # 关闭自动化和日志提示

    service = Service(log_output=os.devnull)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(5)
    return driver


def cookies_web(driver, cookie_path):
    # 设置浏览器的cookie
    print("设置cookie中.....")
    with open(cookie_path, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    cookie_names = {cookie.get("name") for cookie in cookies}
    if not {"auth_token", "ct0"}.issubset(cookie_names):
        print("警告：cookie文件中未检测到完整登录cookie(auth_token/ct0)")

    added_count = 0
    for cookie in cookies:
        cookie = normalize_cookie_for_selenium(cookie)
        try:
            driver.add_cookie(cookie)
            added_count += 1
        except Exception as error:
            print(f'跳过无效cookie: {cookie.get("name")} ({short_error(error)})')
    print(f"已设置 {added_count}/{len(cookies)} 个 cookie")


def get_twitter_name(driver):
    # 获取Twitter用户的名称
    name = driver.find_elements(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div/div/div/div/div/div[2]/div/h2/div/div/div/div/span[1]/span/span[1]')
    folder = name[0].text.replace('/', '-')  # 防止斜杠视作创建多级文件夹

    return folder
