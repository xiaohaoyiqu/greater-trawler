import argparse
import csv
import ctypes
import json
import io
import importlib
import os
import subprocess
import platform
import shutil
import sys
import threading
import time
import traceback
import urllib.request
import zipfile

try:
    import winreg
except ImportError:
    winreg = None
from datetime import datetime
from pathlib import Path
try:
    from tkinter import (
        Tk, Button, Checkbutton, Entry, Frame, Label, Spinbox, StringVar, BooleanVar,
        DISABLED, NORMAL, filedialog, messagebox
    )
    from tkinter.constants import E, W
    TK_AVAILABLE = True
except ImportError:
    Tk = Button = Checkbutton = Entry = Frame = Label = Spinbox = StringVar = BooleanVar = None
    DISABLED = NORMAL = filedialog = messagebox = None
    E = W = None
    TK_AVAILABLE = False

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


__version__ = "1.1.0"


class GoogleImageSearchTool:
    IMAGE_SIZE_LIMIT_MB = 5
    MAX_RESULTS_LIMIT = 500
    DEFAULT_MAX_RESULTS = 50
    DEFAULT_FOLDER_DEPTH = 4
    MAX_FOLDER_DEPTH = 8
    SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    def __init__(self, root):
        self.root = root
        self.root.title(f"谷歌相似图片搜索工具 v{__version__}")
        self.root.geometry("920x760")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f5")

        try:
            if platform.system() == "Windows":
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        self.app_dir = self._get_app_dir()
        self.image_path = ""
        self.driver_path = ""
        self.active_driver = None
        self.driver_lock = threading.Lock()
        self.worker_running = False
        self.driver_selected_manually = False

        self.manual_image_path = StringVar()
        self.manual_folder_path = StringVar()
        self.folder_path = ""
        self.folder_has_images = False
        self.max_results_var = StringVar(value=str(self.DEFAULT_MAX_RESULTS))
        self.keep_browser_var = BooleanVar(value=False)
        self.save_csv_var = BooleanVar(value=True)
        self.include_subdirs_var = BooleanVar(value=False)
        self.folder_depth_var = StringVar(value=str(self.DEFAULT_FOLDER_DEPTH))
        self.proxy_auto = self._get_system_proxy()
        self.headless = False
        self.chrome_binary = ""

        self._init_ui()
        self._refresh_controls()
        threading.Thread(target=self._auto_detect_driver, daemon=True).start()

    def _init_ui(self):
        title_label = Label(
            self.root, text="谷歌相似图片搜索工具", bg="#f5f5f5",
            font=("微软雅黑", 14, "bold"), fg="#2c3e50"
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=18)

        proxy_label = Label(
            self.root, text="网络代理（格式：ip:port）：", bg="#f5f5f5",
            font=("微软雅黑", 10), fg="#34495e"
        )
        proxy_label.grid(row=1, column=0, padx=20, pady=8, sticky=E)

        self.proxy_entry = Entry(self.root, width=42, font=("微软雅黑", 10))
        self.proxy_entry.insert(0, self.proxy_auto if self.proxy_auto else "无需代理请留空")
        self.proxy_entry.grid(row=1, column=1, pady=8, sticky=W)

        driver_label = Label(
            self.root, text="Chrome驱动路径：", bg="#f5f5f5",
            font=("微软雅黑", 10), fg="#34495e"
        )
        driver_label.grid(row=2, column=0, padx=20, pady=8, sticky=E)

        self.driver_display = Entry(self.root, width=42, font=("微软雅黑", 10), state=DISABLED)
        self.driver_display.grid(row=2, column=1, pady=8, sticky=W)

        driver_btn = Button(
            self.root, text="选择驱动", command=self._select_driver,
            font=("微软雅黑", 9), bg="#3498db", fg="white",
            width=10, relief="flat"
        )
        driver_btn.grid(row=2, column=2, padx=10, pady=8, sticky=W)

        image_label = Label(
            self.root, text="图片文件路径：", bg="#f5f5f5",
            font=("微软雅黑", 10), fg="#34495e"
        )
        image_label.grid(row=3, column=0, padx=20, pady=8, sticky=E)

        self.image_entry = Entry(
            self.root, textvariable=self.manual_image_path,
            width=42, font=("微软雅黑", 10)
        )
        self.image_entry.grid(row=3, column=1, pady=8, sticky=W)

        image_btn = Button(
            self.root, text="选择图片", command=self._select_image,
            font=("微软雅黑", 9), bg="#2ecc71", fg="white",
            width=10, relief="flat"
        )
        image_btn.grid(row=3, column=2, padx=10, pady=8, sticky=W)

        folder_label = Label(
            self.root, text="图片文件夹路径：", bg="#f5f5f5",
            font=("微软雅黑", 10), fg="#34495e"
        )
        folder_label.grid(row=4, column=0, padx=20, pady=8, sticky=E)

        self.folder_entry = Entry(
            self.root, textvariable=self.manual_folder_path,
            width=42, font=("微软雅黑", 10)
        )
        self.folder_entry.grid(row=4, column=1, pady=8, sticky=W)

        folder_btn = Button(
            self.root, text="选择文件夹", command=self._select_folder,
            font=("微软雅黑", 9), bg="#16a085", fg="white",
            width=10, relief="flat"
        )
        folder_btn.grid(row=4, column=2, padx=10, pady=8, sticky=W)

        folder_options_frame = Frame(self.root, bg="#f5f5f5")
        folder_options_frame.grid(row=5, column=1, columnspan=2, sticky=W, pady=4)

        self.include_subdirs_check = Checkbutton(
            folder_options_frame, text="包含子文件夹", variable=self.include_subdirs_var,
            bg="#f5f5f5", font=("微软雅黑", 9), fg="#34495e",
            activebackground="#f5f5f5", command=self._check_folder_valid
        )
        self.include_subdirs_check.grid(row=0, column=0, padx=(0, 18), sticky=W)

        depth_label = Label(
            folder_options_frame, text="最大层数", bg="#f5f5f5",
            font=("微软雅黑", 9), fg="#34495e"
        )
        depth_label.grid(row=0, column=1, sticky=W)

        self.folder_depth_spin = Spinbox(
            folder_options_frame, from_=1, to=self.MAX_FOLDER_DEPTH, increment=1,
            textvariable=self.folder_depth_var, width=5, font=("微软雅黑", 9),
            command=self._check_folder_valid
        )
        self.folder_depth_spin.grid(row=0, column=2, padx=(6, 0), sticky=W)

        count_label = Label(
            self.root, text="最大提取数量：", bg="#f5f5f5",
            font=("微软雅黑", 10), fg="#34495e"
        )
        count_label.grid(row=6, column=0, padx=20, pady=8, sticky=E)

        self.max_results_spin = Spinbox(
            self.root, from_=1, to=self.MAX_RESULTS_LIMIT, increment=10,
            textvariable=self.max_results_var, width=8, font=("微软雅黑", 10)
        )
        self.max_results_spin.grid(row=6, column=1, pady=8, sticky=W)

        options_frame = Frame(self.root, bg="#f5f5f5")
        options_frame.grid(row=7, column=1, columnspan=2, sticky=W, pady=4)

        self.keep_browser_check = Checkbutton(
            options_frame, text="搜索结束后保留浏览器", variable=self.keep_browser_var,
            bg="#f5f5f5", font=("微软雅黑", 9), fg="#34495e",
            activebackground="#f5f5f5"
        )
        self.keep_browser_check.grid(row=0, column=0, padx=(0, 18), sticky=W)

        self.save_csv_check = Checkbutton(
            options_frame, text="同时导出CSV", variable=self.save_csv_var,
            bg="#f5f5f5", font=("微软雅黑", 9), fg="#34495e",
            activebackground="#f5f5f5"
        )
        self.save_csv_check.grid(row=0, column=1, sticky=W)

        self.tips_label = Label(
            self.root, bg="#f5f5f5", font=("微软雅黑", 9), fg="#e74c3c",
            text="提示：图片需≤5MB，支持 JPG / PNG / WEBP / GIF；批量模式会按目录保存结果",
            wraplength=760
        )
        self.tips_label.grid(row=8, column=0, columnspan=3, pady=8)

        self.status_label = Label(
            self.root, bg="#f5f5f5", font=("微软雅黑", 10), fg="#7f8c8d",
            text="状态：未选择图片 | 请先选择有效的图片文件", wraplength=760
        )
        self.status_label.grid(row=9, column=0, columnspan=3, pady=8)

        action_frame = Frame(self.root, bg="#f5f5f5")
        action_frame.grid(row=10, column=0, columnspan=3, pady=12)

        self.search_btn = Button(
            action_frame, text="开始搜索相似图片", command=self._run_search,
            font=("微软雅黑", 11, "bold"), bg="#95a5a6", fg="white",
            width=22, height=2, relief="flat", state=DISABLED
        )
        self.search_btn.grid(row=0, column=0, padx=8)

        self.manual_btn = Button(
            action_frame, text="打开浏览器手动上传", command=self._run_open_manual,
            font=("微软雅黑", 10, "bold"), bg="#95a5a6", fg="white",
            width=18, height=2, relief="flat", state=DISABLED
        )
        self.manual_btn.grid(row=0, column=1, padx=8)

        self.batch_btn = Button(
            action_frame, text="批量搜索文件夹", command=self._run_batch_search,
            font=("微软雅黑", 10, "bold"), bg="#95a5a6", fg="white",
            width=18, height=2, relief="flat", state=DISABLED
        )
        self.batch_btn.grid(row=0, column=2, padx=8)

        browser_frame = Frame(self.root, bg="#f5f5f5")
        browser_frame.grid(row=11, column=0, columnspan=3, pady=4)

        self.extract_btn = Button(
            browser_frame, text="从当前浏览器提取链接", command=self._run_extract_current,
            font=("微软雅黑", 10), bg="#95a5a6", fg="white",
            width=20, relief="flat", state=DISABLED
        )
        self.extract_btn.grid(row=0, column=0, padx=8)

        self.close_browser_btn = Button(
            browser_frame, text="关闭浏览器", command=self._close_active_driver,
            font=("微软雅黑", 10), bg="#95a5a6", fg="white",
            width=12, relief="flat", state=DISABLED
        )
        self.close_browser_btn.grid(row=0, column=1, padx=8)

        self.log_label = Label(
            self.root, bg="#f5f5f5", font=("微软雅黑", 9), fg="#7f8c8d",
            text="日志：正在检测ChromeDriver...", wraplength=760, justify="left"
        )
        self.log_label.grid(row=12, column=0, columnspan=3, pady=14)

        self.manual_image_path.trace_add("write", lambda *_: self._check_image_valid())
        self.manual_folder_path.trace_add("write", lambda *_: self._check_folder_valid())

    def _get_app_dir(self):
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    def _output_dir(self):
        output_dir_override = getattr(self, "output_dir_override", "")
        if output_dir_override:
            output_dir = Path(output_dir_override).expanduser().resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir

        desktop = Path.home() / "Desktop"
        if desktop.exists():
            return desktop
        output_dir = self.app_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _run_on_ui(self, callback):
        try:
            if threading.current_thread() is threading.main_thread():
                callback()
            else:
                self.root.after(0, callback)
        except RuntimeError:
            pass

    def _set_log(self, text):
        self._run_on_ui(lambda: self.log_label.config(text=text))

    def _set_status(self, text, fg="#7f8c8d"):
        self._run_on_ui(lambda: self.status_label.config(text=text, fg=fg))

    def _driver_ready(self):
        return bool(self.driver_path and os.path.exists(self.driver_path))

    def _has_active_driver(self):
        with self.driver_lock:
            return self.active_driver is not None

    def _get_active_driver(self):
        with self.driver_lock:
            return self.active_driver

    def _set_active_driver(self, driver):
        with self.driver_lock:
            self.active_driver = driver
        self._run_on_ui(self._refresh_controls)

    def _refresh_controls(self):
        driver_ready = self._driver_ready()
        has_browser = self._has_active_driver()
        image_ready = bool(self.image_path and os.path.exists(self.image_path))
        folder_ready = bool(self.folder_path and os.path.isdir(self.folder_path) and getattr(self, "folder_has_images", True))

        search_ready = driver_ready and image_ready and not self.worker_running
        manual_ready = driver_ready and not has_browser and not self.worker_running
        batch_ready = driver_ready and folder_ready and not has_browser and not self.worker_running
        extract_ready = has_browser and not self.worker_running
        close_ready = has_browser

        self.search_btn.config(
            state=NORMAL if search_ready else DISABLED,
            bg="#27ae60" if search_ready else "#95a5a6"
        )
        self.manual_btn.config(
            state=NORMAL if manual_ready else DISABLED,
            bg="#2980b9" if manual_ready else "#95a5a6"
        )
        self.batch_btn.config(
            state=NORMAL if batch_ready else DISABLED,
            bg="#16a085" if batch_ready else "#95a5a6"
        )
        self.extract_btn.config(
            state=NORMAL if extract_ready else DISABLED,
            bg="#8e44ad" if extract_ready else "#95a5a6"
        )
        self.close_browser_btn.config(
            state=NORMAL if close_ready else DISABLED,
            bg="#e67e22" if close_ready else "#95a5a6"
        )

    def _set_worker_running(self, running):
        def apply():
            self.worker_running = running
            self._refresh_controls()
        self._run_on_ui(apply)

    def _get_system_proxy(self):
        if platform.system() == "Windows" and winreg is not None:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
                )
                proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                if proxy_enable:
                    proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    return proxy_server
            except Exception:
                pass

        for name in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
            proxy = os.environ.get(name, "").strip()
            if proxy:
                return proxy
        return ""

    def _find_existing_driver(self):
        names = ["chromedriver.exe"] if platform.system() == "Windows" else ["chromedriver"]
        for name in names:
            candidate = self.app_dir / name
            if candidate.exists():
                return str(candidate)
        return ""

    def _get_chrome_version(self):
        if platform.system() == "Windows" and winreg is not None:
            registry_locations = [
                (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Google\Chrome\BLBeacon"),
            ]
            for root_key, key_path in registry_locations:
                try:
                    key = winreg.OpenKey(root_key, key_path)
                    version = winreg.QueryValueEx(key, "version")[0]
                    if version:
                        return version
                except Exception:
                    pass

        exe_locations = []
        chrome_binary = getattr(self, "chrome_binary", "")
        if chrome_binary:
            exe_locations.append(Path(chrome_binary))

        if platform.system() == "Windows":
            exe_locations.extend([
                Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            ])
            command_names = ["chrome.exe", "chrome"]
        elif platform.system() == "Darwin":
            exe_locations.extend([
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
            ])
            command_names = ["google-chrome", "chrome", "chromium"]
        else:
            exe_locations.extend([
                Path("/usr/bin/google-chrome"),
                Path("/usr/bin/google-chrome-stable"),
                Path("/usr/bin/chromium"),
                Path("/usr/bin/chromium-browser"),
                Path("/snap/bin/chromium"),
            ])
            command_names = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]

        for command in command_names:
            resolved = shutil.which(command)
            if resolved:
                exe_locations.append(Path(resolved))

        seen = set()
        for chrome_exe in exe_locations:
            chrome_exe = Path(chrome_exe)
            if str(chrome_exe) in seen or not chrome_exe.exists():
                continue
            seen.add(str(chrome_exe))
            try:
                kwargs = {"capture_output": True, "text": True, "timeout": 5}
                if platform.system() == "Windows":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                completed = subprocess.run([str(chrome_exe), "--version"], **kwargs)
                output = f"{completed.stdout} {completed.stderr}"
                for part in output.split():
                    if part[:1].isdigit():
                        return part.strip()
            except Exception:
                pass
        return ""

    def _driver_platform_name(self):
        if platform.system() == "Windows":
            return "win64" if sys.maxsize > 2 ** 32 else "win32"
        if platform.system() == "Darwin":
            machine = platform.machine().lower()
            return "mac-arm64" if "arm" in machine else "mac-x64"
        return "linux64"

    def _normalized_proxy_map(self):
        proxy = self.proxy_auto
        try:
            if hasattr(self, "proxy_entry"):
                entry_proxy = self.proxy_entry.get().strip()
                if entry_proxy and entry_proxy != "无需代理请留空":
                    proxy = entry_proxy
        except Exception:
            pass

        if not proxy:
            return {}

        def with_scheme(value):
            if "://" in value:
                return value
            return "http://" + value

        if ";" in proxy:
            result = {}
            for part in proxy.split(";"):
                if "=" not in part:
                    continue
                scheme, value = part.split("=", 1)
                scheme = scheme.strip().lower()
                value = value.strip()
                if scheme in {"http", "https"} and value:
                    result[scheme] = with_scheme(value)
            return result

        proxy_url = with_scheme(proxy.strip())
        return {"http": proxy_url, "https": proxy_url}

    def _download_url(self, url, timeout=60):
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        proxy_map = self._normalized_proxy_map()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxy_map)) if proxy_map else urllib.request.build_opener()
        with opener.open(request, timeout=timeout) as response:
            return response.read()

    def _select_chromedriver_download(self, downloads):
        platform_name = self._driver_platform_name()
        for item in downloads or []:
            if item.get("platform") == platform_name:
                return item.get("url")
        return ""

    def _find_chromedriver_download_url(self, chrome_version):
        platform_name = self._driver_platform_name()
        major = chrome_version.split(".", 1)[0] if chrome_version else ""
        build = ".".join(chrome_version.split(".")[:3]) if chrome_version else ""

        endpoints = []
        if build:
            endpoints.append((
                "builds", build,
                "https://googlechromelabs.github.io/chrome-for-testing/latest-patch-versions-per-build-with-downloads.json"
            ))
        if major:
            endpoints.append((
                "milestones", major,
                "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"
            ))
        endpoints.append((
            "channels", "Stable",
            "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
        ))

        for group, key, url in endpoints:
            data = json.loads(self._download_url(url).decode("utf-8"))
            entry = data.get(group, {}).get(key, {})
            driver_url = self._select_chromedriver_download(
                entry.get("downloads", {}).get("chromedriver")
            )
            if driver_url:
                self._set_log(f"日志：匹配ChromeDriver平台 {platform_name} → {entry.get('version', chrome_version)}")
                return driver_url
        raise RuntimeError("无法从Chrome for Testing获取ChromeDriver下载地址")

    def _download_chromedriver_to_app_dir(self):
        chrome_version = self._get_chrome_version()
        if chrome_version:
            self._set_log(f"日志：检测到Chrome版本 → {chrome_version}")
        else:
            self._set_log("日志：未检测到Chrome版本，将下载稳定版ChromeDriver")

        download_url = self._find_chromedriver_download_url(chrome_version)
        self._set_log("日志：正在下载ChromeDriver...")
        zip_bytes = self._download_url(download_url, timeout=180)
        target_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
        target = self.app_dir / target_name

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            driver_member = ""
            for name in archive.namelist():
                if name.replace("\\", "/").endswith("/" + target_name) or name == target_name:
                    driver_member = name
                    break
            if not driver_member:
                raise RuntimeError("ChromeDriver压缩包中未找到驱动文件")
            target.write_bytes(archive.read(driver_member))
        if platform.system() != "Windows":
            target.chmod(target.stat().st_mode | 0o755)

        return str(target)

    def _load_autodriver(self):
        try:
            return importlib.import_module("toollib.autodriver")
        except Exception:
            try:
                package = importlib.import_module("toollib")
                return getattr(package, "autodriver", None)
            except Exception:
                return None
    def _copy_driver_to_app_dir(self, driver_path):
        source = Path(driver_path).resolve()
        if not source.exists():
            return str(source)

        target_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
        target = self.app_dir / target_name
        try:
            if source != target.resolve():
                shutil.copy2(source, target)
            if platform.system() != "Windows":
                target.chmod(target.stat().st_mode | 0o755)
            return str(target)
        except Exception:
            return str(source)

    def _update_driver_display(self):
        def apply():
            self.driver_display.config(state=NORMAL)
            self.driver_display.delete(0, "end")
            self.driver_display.insert(0, self.driver_path)
            self.driver_display.config(state=DISABLED)
            self._refresh_controls()
        self._run_on_ui(apply)

    def _auto_detect_driver(self):
        try:
            existing_driver = self._find_existing_driver()
            if existing_driver:
                self.driver_path = existing_driver
                self._update_driver_display()
                self._set_log(f"日志：使用同级目录ChromeDriver → {Path(existing_driver).name}")
                return

            self._set_log("日志：正在自动匹配ChromeDriver...")
            try:
                detected_driver = self._download_chromedriver_to_app_dir()
            except Exception as download_error:
                autodriver_module = self._load_autodriver()
                if autodriver_module is None:
                    raise download_error
                self._set_log("日志：内置下载失败，正在尝试toollib自动驱动...")
                detected_driver = autodriver_module.chromedriver()

            if self.driver_selected_manually:
                return

            self.driver_path = self._copy_driver_to_app_dir(detected_driver)
            self._update_driver_display()
            self._set_log(f"日志：自动匹配ChromeDriver → {Path(self.driver_path).name}")
        except Exception as e:
            self._set_log(f"日志：自动获取驱动失败，请手动选择 → {str(e)[:80]}")
        finally:
            self._run_on_ui(self._refresh_controls)

    def _select_driver(self):
        driver_path = filedialog.askopenfilename(
            title="选择ChromeDriver可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if driver_path:
            self.driver_selected_manually = True
            self.driver_path = driver_path
            self._update_driver_display()
            self._set_log(f"日志：已手动选择驱动 → {os.path.basename(driver_path)}")
            self._check_image_valid()

    def _select_image(self):
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp *.gif"), ("所有文件", "*.*")]
        )
        if file_path:
            self.manual_image_path.set(file_path)
            self._check_image_valid()

    def _detect_image_type(self, header):
        if header.startswith(b"\xff\xd8\xff"):
            return "JPG"
        if header.startswith(b"\x89PNG"):
            return "PNG"
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "WEBP"
        if header.startswith((b"GIF87a", b"GIF89a")):
            return "GIF"
        return ""

    def _check_image_valid(self):
        file_path = self.manual_image_path.get().strip().strip('"')
        self.image_path = ""

        if not file_path:
            self._set_status("状态：未选择图片 | 请先选择有效的图片文件", "#e74c3c")
            self._run_on_ui(self._refresh_controls)
            return False

        if not os.path.exists(file_path):
            self._set_status("状态：图片文件不存在 | 请检查路径是否正确", "#e74c3c")
            self._set_log("日志：图片文件不存在")
            self._run_on_ui(self._refresh_controls)
            return False

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size > self.IMAGE_SIZE_LIMIT_MB:
            self._set_status(
                f"状态：图片过大（{file_size:.1f}MB）| 请压缩至{self.IMAGE_SIZE_LIMIT_MB}MB以内",
                "#e74c3c"
            )
            self._set_log(f"日志：图片大小{file_size:.1f}MB，超过限制")
            self._run_on_ui(self._refresh_controls)
            return False

        try:
            with open(file_path, "rb") as f:
                image_type = self._detect_image_type(f.read(12))
            if not image_type:
                self._set_status("状态：无效图片格式 | 仅支持JPG / PNG / WEBP / GIF", "#e74c3c")
                self._set_log("日志：文件不是有效的JPG / PNG / WEBP / GIF图片")
                self._run_on_ui(self._refresh_controls)
                return False
        except Exception:
            self._set_status("状态：无法验证图片 | 请确认是真实的图片文件", "#e74c3c")
            self._set_log("日志：无法验证图片格式")
            self._run_on_ui(self._refresh_controls)
            return False

        self.image_path = file_path
        if self._driver_ready():
            self._set_status(f"状态：图片有效 | 已选择：{os.path.basename(file_path)}", "#27ae60")
        else:
            self._set_status("状态：图片有效 | 请等待自动驱动或手动选择ChromeDriver", "#f39c12")
        self._set_log(f"日志：图片验证通过 → {os.path.basename(file_path)}")
        self._run_on_ui(self._refresh_controls)
        return True

    def _select_folder(self):
        folder_path = filedialog.askdirectory(title="选择图片文件夹")
        if folder_path:
            self.manual_folder_path.set(folder_path)
            self._check_folder_valid()

    def _get_folder_depth(self):
        try:
            value = int(str(self.folder_depth_var.get()).strip())
        except ValueError:
            value = self.DEFAULT_FOLDER_DEPTH
        value = max(1, min(value, self.MAX_FOLDER_DEPTH))
        self.folder_depth_var.set(str(value))
        return value

    def _check_folder_valid(self):
        folder_path = self.manual_folder_path.get().strip().strip('"')
        self.folder_path = ""
        self.folder_has_images = False

        if not folder_path:
            self._run_on_ui(self._refresh_controls)
            return False

        if not os.path.isdir(folder_path):
            self._set_status("状态：图片文件夹不存在 | 请检查路径是否正确", "#e74c3c")
            self._set_log("日志：图片文件夹不存在")
            self._run_on_ui(self._refresh_controls)
            return False

        self.folder_path = folder_path
        include_subdirs = self.include_subdirs_var.get()
        max_depth = self._get_folder_depth() if include_subdirs else 1
        images, skipped = self._scan_image_files(folder_path, include_subdirs, max_depth)
        mode_text = f"包含子文件夹，最大{max_depth}层" if include_subdirs else "仅当前文件夹"
        if images:
            self._set_status(f"状态：文件夹有效 | {mode_text} | 可处理 {len(images)} 张图片", "#27ae60")
            self._set_log(f"日志：文件夹扫描完成，可处理 {len(images)} 张，跳过 {len(skipped)} 个无效/超限文件")
        else:
            self._set_status(f"状态：文件夹内没有可处理图片 | {mode_text}", "#e74c3c")
            self._set_log(f"日志：未找到支持格式图片，跳过 {len(skipped)} 个无效/超限文件")
        self.folder_has_images = bool(images)
        self._run_on_ui(self._refresh_controls)
        return bool(images)

    def _is_supported_image_file(self, file_path):
        path = Path(file_path)
        if path.suffix.lower() not in self.SUPPORTED_IMAGE_EXTENSIONS:
            return False, "unsupported_extension"
        try:
            if path.stat().st_size / (1024 * 1024) > self.IMAGE_SIZE_LIMIT_MB:
                return False, "file_too_large"
            with open(path, "rb") as f:
                if not self._detect_image_type(f.read(12)):
                    return False, "invalid_image_header"
        except Exception as e:
            return False, str(e)
        return True, ""

    def _scan_image_files(self, folder_path, include_subdirs=False, max_depth=1):
        root = Path(folder_path).expanduser().resolve()
        max_depth = max(1, min(int(max_depth), self.MAX_FOLDER_DEPTH))
        images = []
        skipped = []

        if not include_subdirs:
            candidates = [p for p in root.iterdir() if p.is_file()]
            for candidate in sorted(candidates, key=lambda p: p.name.lower()):
                ok, reason = self._is_supported_image_file(candidate)
                if ok:
                    images.append(candidate)
                elif candidate.suffix.lower() in self.SUPPORTED_IMAGE_EXTENSIONS:
                    skipped.append((candidate, reason))
            return images, skipped

        for current_root, dirs, files in os.walk(root):
            current_path = Path(current_root)
            try:
                relative = current_path.relative_to(root)
                current_depth = 1 if str(relative) == "." else len(relative.parts) + 1
            except ValueError:
                current_depth = 1

            if current_depth >= max_depth:
                dirs[:] = []
            elif current_depth > max_depth:
                dirs[:] = []
                continue

            for filename in sorted(files, key=str.lower):
                candidate = current_path / filename
                ok, reason = self._is_supported_image_file(candidate)
                if ok:
                    images.append(candidate)
                elif candidate.suffix.lower() in self.SUPPORTED_IMAGE_EXTENSIONS:
                    skipped.append((candidate, reason))

        return images, skipped

    def _format_batch_file_names(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"谷歌图片批量搜索结果_{stamp}.txt", f"谷歌图片批量搜索结果_{stamp}.csv"

    def _save_batch_results(self, records_by_dir, save_csv=True):
        saved_paths = []
        txt_name, csv_name = self._format_batch_file_names()

        for directory, records in sorted(records_by_dir.items(), key=lambda item: str(item[0]).lower()):
            directory = Path(directory)
            txt_path = directory / txt_name
            success_count = sum(1 for record in records if record.get("links"))
            error_count = sum(1 for record in records if record.get("error"))
            no_result_count = len(records) - success_count - error_count

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("=== 谷歌相似图片批量搜索结果 ===\n")
                f.write(f"目录：{directory}\n")
                f.write(f"提取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"图片数量：{len(records)}\n")
                f.write(f"成功图片：{success_count}\n")
                f.write(f"无结果图片：{no_result_count}\n")
                f.write(f"失败图片：{error_count}\n")
                f.write("================================\n\n")
                for image_idx, record in enumerate(records, 1):
                    f.write(f"[{image_idx}] {record['image'].name}\n")
                    f.write(f"路径：{record['image']}\n")
                    if record.get("error"):
                        f.write(f"状态：失败 | {record['error']}\n\n")
                        continue
                    links = record.get("links", [])
                    f.write(f"状态：{'成功' if links else '无结果'} | 链接数量：{len(links)}\n")
                    for link_idx, link in enumerate(links, 1):
                        f.write(f"  {link_idx}. {link}\n")
                    f.write("\n")
            saved_paths.append(txt_path)

            if save_csv:
                csv_path = directory / csv_name
                with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["image_index", "image_name", "image_path", "status", "url_index", "url", "error"])
                    for image_idx, record in enumerate(records, 1):
                        links = record.get("links", [])
                        error = record.get("error", "")
                        status = "error" if error else ("success" if links else "no_result")
                        if links:
                            for link_idx, link in enumerate(links, 1):
                                writer.writerow([image_idx, record["image"].name, str(record["image"]), status, link_idx, link, error])
                        else:
                            writer.writerow([image_idx, record["image"].name, str(record["image"]), status, "", "", error])
                saved_paths.append(csv_path)

        return saved_paths

    def _run_batch_search(self):
        if self.worker_running:
            return
        if self._has_active_driver():
            messagebox.showwarning("浏览器未关闭", "请先关闭当前浏览器，再开始批量搜索")
            return
        if not self._check_folder_valid():
            return

        max_results = self._get_max_results()
        if max_results is None:
            return
        if not self._driver_ready():
            messagebox.showerror("缺少驱动", "未找到有效的ChromeDriver，请等待自动检测或手动选择")
            return

        include_subdirs = self.include_subdirs_var.get()
        max_depth = self._get_folder_depth() if include_subdirs else 1
        images, skipped = self._scan_image_files(self.folder_path, include_subdirs, max_depth)
        if not images:
            messagebox.showwarning("没有图片", "文件夹中没有可处理的图片")
            return

        proxy = self.proxy_entry.get().strip()
        if proxy == "无需代理请留空":
            proxy = ""

        options = {
            "driver_path": self.driver_path,
            "proxy": proxy,
            "max_results": max_results,
            "keep_browser": self.keep_browser_var.get(),
            "save_csv": self.save_csv_var.get(),
            "images": images,
            "skipped": skipped,
        }
        self._set_worker_running(True)
        threading.Thread(target=self._batch_search_worker, args=(options,), daemon=True).start()

    def _batch_search_worker(self, options):
        driver = None
        records_by_dir = {}
        try:
            self._set_log(f"日志：正在启动Chrome浏览器，准备批量处理 {len(options['images'])} 张图片...")
            driver = self._init_chrome(options["driver_path"], options["proxy"])
            self._set_active_driver(driver)

            for index, image_path in enumerate(options["images"], 1):
                image_path = Path(image_path)
                self._set_log(f"日志：批量处理中 {index}/{len(options['images'])} → {image_path.name}")
                record = {"image": image_path, "links": [], "error": ""}
                try:
                    self._upload_image(driver, str(image_path))
                    record["links"] = self._extract_links(driver, options["max_results"])
                except Exception as e:
                    record["error"] = str(e)[:300]
                    try:
                        self._save_debug_files(driver, image_path.parent)
                    except Exception:
                        pass
                records_by_dir.setdefault(image_path.parent, []).append(record)

            if records_by_dir:
                saved_paths = self._save_batch_results(records_by_dir, options["save_csv"])
                success_images = sum(1 for records in records_by_dir.values() for record in records if record.get("links"))
                total_links = sum(len(record.get("links", [])) for records in records_by_dir.values() for record in records)
                self._set_status(
                    f"状态：批量完成 | 图片 {len(options['images'])} 张 | 成功 {success_images} 张 | 链接 {total_links} 个",
                    "#27ae60"
                )
                self._set_log(f"日志：批量结果已按目录保存，共生成 {len(saved_paths)} 个文件，跳过 {len(options['skipped'])} 个无效/超限文件")
            else:
                self._set_status("状态：批量完成 | 没有生成结果", "#f39c12")
        except Exception as e:
            if driver:
                try:
                    debug_dir = self._save_debug_files(driver)
                    self._set_log(f"日志：批量搜索异常 → {e} | 调试文件：{debug_dir}")
                except Exception:
                    self._set_log(f"日志：批量搜索异常 → {e}")
            else:
                self._set_log(f"日志：批量搜索异常 → {e}")
            self._set_status(f"状态：批量搜索失败 | {str(e)[:60]}", "#e74c3c")
        finally:
            if driver and options.get("keep_browser"):
                self._set_log("日志：浏览器已保留，可继续检查页面")
            elif driver:
                self._quit_driver(driver)
                self._set_active_driver(None)
            self._set_worker_running(False)
    def _get_max_results(self):
        try:
            value = int(str(self.max_results_var.get()).strip())
        except ValueError:
            messagebox.showerror("数量无效", "最大提取数量必须是数字")
            return None

        value = max(1, min(value, self.MAX_RESULTS_LIMIT))
        self.max_results_var.set(str(value))
        return value

    def _collect_run_options(self, require_image):
        max_results = self._get_max_results()
        if max_results is None:
            return None

        if not self._driver_ready():
            messagebox.showerror("缺少驱动", "未找到有效的ChromeDriver，请等待自动检测或手动选择")
            return None

        if require_image:
            if not self._check_image_valid():
                return None
            image_path = self.image_path
        else:
            image_path = self.image_path

        proxy = self.proxy_entry.get().strip()
        if proxy == "无需代理请留空":
            proxy = ""

        return {
            "driver_path": self.driver_path,
            "image_path": image_path,
            "proxy": proxy,
            "max_results": max_results,
            "keep_browser": self.keep_browser_var.get(),
            "save_csv": self.save_csv_var.get(),
        }

    def _init_chrome(self, driver_path, proxy):
        if not driver_path or not os.path.exists(driver_path):
            raise Exception("未找到有效的ChromeDriver，请先手动选择")

        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=zh-CN")
        chrome_options.add_argument("--window-size=1365,900")
        chrome_binary = getattr(self, "chrome_binary", "")
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
        if getattr(self, "headless", False):
            chrome_options.add_argument("--headless=new")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        if proxy:
            chrome_options.add_argument(f"--proxy-server={proxy}")
            chrome_options.add_argument("--ignore-certificate-errors")

        try:
            service = Service(driver_path)
            service.log_path = os.devnull
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
                """
            })
            return driver
        except WebDriverException as e:
            raise Exception(f"Chrome启动失败：{str(e)[:120]}")

    def _wait_any_clickable(self, driver, locators, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for by, selector in locators:
                try:
                    elements = driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            return element
                except Exception:
                    continue
            time.sleep(0.4)
        raise TimeoutException("等待可点击元素超时")

    def _wait_file_input(self, driver, timeout=15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            if inputs:
                return inputs[0]
            time.sleep(0.4)
        raise TimeoutException("未找到图片上传输入框")

    def _dismiss_popups(self, driver):
        popup_xpaths = [
            '//button//*[contains(text(), "接受全部")]/ancestor::button',
            '//button//*[contains(text(), "我同意")]/ancestor::button',
            '//button//*[contains(text(), "Accept all")]/ancestor::button',
            '//button//*[contains(text(), "I agree")]/ancestor::button',
            '//button//*[contains(text(), "Reject all")]/ancestor::button',
        ]
        for xpath in popup_xpaths:
            try:
                for button in driver.find_elements(By.XPATH, xpath):
                    if button.is_displayed() and button.is_enabled():
                        button.click()
                        time.sleep(0.5)
                        return
            except Exception:
                continue

    def _upload_image(self, driver, image_path):
        self._set_log("日志：正在访问谷歌图片搜索页面...")
        driver.get("https://images.google.com/")
        time.sleep(2)
        self._dismiss_popups(driver)

        self._set_log("日志：正在定位按图搜索入口...")
        upload_btn = self._wait_any_clickable(driver, [
            (By.CSS_SELECTOR, '[aria-label*="按图搜索"]'),
            (By.CSS_SELECTOR, '[aria-label*="Search by image"]'),
            (By.CSS_SELECTOR, '[aria-label*="Search with an image"]'),
            (By.CSS_SELECTOR, '[title*="按图搜索"]'),
            (By.CSS_SELECTOR, '[title*="Search by image"]'),
            (By.XPATH, '//*[contains(@aria-label, "Google Lens") or contains(@title, "Google Lens")]'),
        ], timeout=20)
        upload_btn.click()
        time.sleep(1)

        self._set_log("日志：正在上传图片文件...")
        file_input = self._wait_file_input(driver, timeout=15)
        file_input.send_keys(image_path)
        self._wait_for_initial_links(driver, timeout=30)

    def _wait_for_initial_links(self, driver, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._extract_links_once(driver):
                return
            time.sleep(1)

    def _extract_links_once(self, driver):
        return driver.execute_script("""
        const urls = new Set();
        const imageExt = /\.(jpg|jpeg|png|webp|gif|bmp|svg|avif)$/i;

        function isBlockedHost(host) {
            host = host.toLowerCase();
            return /(^|\.)google\./.test(host)
                || host === 'google'
                || host.endsWith('.google')
                || host.includes('google')
                || host === 'gstatic.com'
                || host.endsWith('.gstatic.com')
                || host === 'googleusercontent.com'
                || host.endsWith('.googleusercontent.com')
                || host === 'googleapis.com'
                || host.endsWith('.googleapis.com');
        }

        function toUrl(raw) {
            if (!raw) return null;
            let parsed;
            try {
                parsed = new URL(raw, location.href);
            } catch (e) {
                return null;
            }

            const host = parsed.hostname.toLowerCase();
            if (host.includes('google.') && parsed.pathname === '/url') {
                const target = parsed.searchParams.get('q') || parsed.searchParams.get('url');
                if (target) {
                    try { parsed = new URL(target); } catch (e) { return null; }
                }
            }

            if (host.includes('google.') && parsed.pathname.includes('/imgres')) {
                const target = parsed.searchParams.get('imgrefurl') || parsed.searchParams.get('imgurl');
                if (target) {
                    try { parsed = new URL(target); } catch (e) { return null; }
                }
            }

            if (!['http:', 'https:'].includes(parsed.protocol)) return null;
            if (isBlockedHost(parsed.hostname)) return null;
            if (imageExt.test(parsed.pathname)) return null;
            parsed.hash = '';
            return parsed.href;
        }

        document.querySelectorAll('a[href]').forEach(anchor => {
            const href = toUrl(anchor.getAttribute('href'));
            if (href) urls.add(href);
        });
        return Array.from(urls);
        """)

    def _scroll_results(self, driver):
        driver.execute_script("""
        const nodes = [document.scrollingElement, document.documentElement, document.body]
            .concat(Array.from(document.querySelectorAll('div')));
        nodes.forEach(node => {
            if (!node) return;
            if (node.scrollHeight > node.clientHeight + 80) {
                node.scrollTop = node.scrollHeight;
            }
        });
        window.scrollBy(0, Math.max(window.innerHeight, 800));
        """)

    def _extract_links(self, driver, max_results):
        links = []
        seen = set()
        stable_rounds = 0
        last_count = -1
        start = time.time()

        while time.time() - start < 90:
            try:
                page_links = self._extract_links_once(driver)
            except Exception:
                page_links = []

            for link in page_links:
                if link not in seen:
                    seen.add(link)
                    links.append(link)
                    if len(links) >= max_results:
                        return links[:max_results]

            if len(links) == last_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                last_count = len(links)

            if stable_rounds >= 4:
                break

            self._set_log(f"日志：已提取 {len(links)} 个链接，继续滚动加载...")
            self._scroll_results(driver)
            time.sleep(1.4)

        return links[:max_results]

    def _save_links(self, links, save_csv=True):
        if not links:
            return []

        output_dir = self._output_dir()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        txt_path = output_dir / f"谷歌图片搜索结果_{stamp}.txt"
        paths = [txt_path]

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=== 谷歌相似图片网页链接 ===\n")
            f.write(f"提取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"链接数量：{len(links)}\n")
            f.write("============================\n\n")
            for idx, link in enumerate(links, 1):
                f.write(f"{idx}. {link}\n")

        if save_csv:
            csv_path = output_dir / f"谷歌图片搜索结果_{stamp}.csv"
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["index", "url"])
                for idx, link in enumerate(links, 1):
                    writer.writerow([idx, link])
            paths.append(csv_path)

        return paths

    def _save_debug_files(self, driver, output_base=None):
        base_dir = Path(output_base) if output_base else self._output_dir()
        debug_dir = base_dir / "谷歌图片搜索调试"
        debug_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = debug_dir / f"page_{stamp}.html"
        screenshot_path = debug_dir / f"page_{stamp}.png"
        error_path = debug_dir / f"error_{stamp}.log"

        try:
            html_path.write_text(driver.page_source, encoding="utf-8")
        except Exception:
            pass
        try:
            driver.save_screenshot(str(screenshot_path))
        except Exception:
            pass
        try:
            error_path.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        return debug_dir

    def _run_search(self):
        if self.worker_running:
            return
        if self._has_active_driver():
            messagebox.showwarning("浏览器未关闭", "请先关闭当前浏览器，再开始新的搜索")
            return

        options = self._collect_run_options(require_image=True)
        if not options:
            return

        self._set_worker_running(True)
        threading.Thread(target=self._search_worker, args=(options,), daemon=True).start()

    def _search_worker(self, options):
        driver = None
        success = False
        try:
            self._set_log("日志：正在启动Chrome浏览器...")
            driver = self._init_chrome(options["driver_path"], options["proxy"])
            self._set_active_driver(driver)

            self._upload_image(driver, options["image_path"])
            self._set_log("日志：正在提取相关网页链接...")
            links = self._extract_links(driver, options["max_results"])

            if links:
                paths = self._save_links(links, options["save_csv"])
                file_names = "，".join(path.name for path in paths)
                self._set_status(f"状态：成功提取 {len(links)} 个链接 | 已保存到桌面", "#27ae60")
                self._set_log(f"日志：链接已保存 → {file_names}")
                success = True
            else:
                self._set_status("状态：未提取到有效链接 | 可尝试手动上传后再提取", "#e74c3c")
                self._set_log("日志：未提取到任何有效网页链接")
        except Exception as e:
            if driver:
                debug_dir = self._save_debug_files(driver)
                self._set_log(f"日志：搜索异常 → {e} | 调试文件：{debug_dir}")
            else:
                self._set_log(f"日志：搜索异常 → {e}")
            self._set_status(f"状态：搜索失败 | {str(e)[:60]}", "#e74c3c")
        finally:
            if driver and options["keep_browser"]:
                if not success:
                    self._set_status("状态：浏览器已保留 | 可手动处理后点击提取", "#f39c12")
                self._set_log("日志：浏览器已保留，可继续检查页面或手动提取")
            elif driver:
                self._quit_driver(driver)
                self._set_active_driver(None)
            self._set_worker_running(False)

    def _run_open_manual(self):
        if self.worker_running:
            return
        if self._has_active_driver():
            messagebox.showwarning("浏览器未关闭", "当前已有浏览器，请先关闭后再打开新的浏览器")
            return

        options = self._collect_run_options(require_image=False)
        if not options:
            return

        self._set_worker_running(True)
        threading.Thread(target=self._manual_open_worker, args=(options,), daemon=True).start()

    def _manual_open_worker(self, options):
        driver = None
        try:
            self._set_log("日志：正在启动Chrome浏览器...")
            driver = self._init_chrome(options["driver_path"], options["proxy"])
            self._set_active_driver(driver)
            driver.get("https://images.google.com/")
            time.sleep(2)
            self._dismiss_popups(driver)
            self._set_status("状态：浏览器已打开 | 手动上传图片后点击提取", "#27ae60")
            self._set_log("日志：请在浏览器中手动完成上传/验证，然后点击“从当前浏览器提取链接”")
        except Exception as e:
            if driver:
                self._quit_driver(driver)
                self._set_active_driver(None)
            self._set_status(f"状态：打开浏览器失败 | {str(e)[:60]}", "#e74c3c")
            self._set_log(f"日志：打开浏览器异常 → {e}")
        finally:
            self._set_worker_running(False)

    def _run_extract_current(self):
        if self.worker_running:
            return

        driver = self._get_active_driver()
        if not driver:
            messagebox.showwarning("无浏览器", "当前没有由本工具打开的浏览器")
            return

        max_results = self._get_max_results()
        if max_results is None:
            return

        save_csv = self.save_csv_var.get()
        self._set_worker_running(True)
        threading.Thread(
            target=self._extract_current_worker,
            args=(driver, max_results, save_csv),
            daemon=True
        ).start()

    def _extract_current_worker(self, driver, max_results, save_csv):
        try:
            self._set_log("日志：正在从当前浏览器页面提取链接...")
            links = self._extract_links(driver, max_results)
            if links:
                paths = self._save_links(links, save_csv)
                file_names = "，".join(path.name for path in paths)
                self._set_status(f"状态：成功提取 {len(links)} 个链接 | 已保存到桌面", "#27ae60")
                self._set_log(f"日志：链接已保存 → {file_names}")
            else:
                self._set_status("状态：未提取到有效链接 | 请确认当前页面已有搜索结果", "#e74c3c")
                self._set_log("日志：当前页面未找到有效外部链接")
        except Exception as e:
            self._set_status(f"状态：提取失败 | {str(e)[:60]}", "#e74c3c")
            self._set_log(f"日志：提取异常 → {e}")
        finally:
            self._set_worker_running(False)

    def _quit_driver(self, driver):
        try:
            driver.quit()
        except Exception:
            pass

    def _close_active_driver(self):
        driver = self._get_active_driver()
        if not driver:
            return

        self._set_active_driver(None)
        self._set_log("日志：正在关闭浏览器...")
        threading.Thread(target=self._close_driver_worker, args=(driver,), daemon=True).start()

    def _close_driver_worker(self, driver):
        self._quit_driver(driver)
        self._set_status("状态：浏览器已关闭", "#7f8c8d")
        self._set_log("日志：浏览器已关闭")
        self._run_on_ui(self._refresh_controls)


class ConsoleLabel:
    def config(self, **kwargs):
        text = kwargs.get("text")
        if text:
            print(text, flush=True)


class SimpleValue:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _create_cli_tool(args):
    tool = GoogleImageSearchTool.__new__(GoogleImageSearchTool)
    tool.root = None
    tool.app_dir = tool._get_app_dir()
    tool.image_path = ""
    tool.driver_path = args.driver or ""
    tool.active_driver = None
    tool.driver_lock = threading.Lock()
    tool.worker_running = False
    tool.driver_selected_manually = bool(args.driver)
    tool.output_dir_override = args.output_dir or ""
    tool.headless = args.headless
    tool.chrome_binary = args.chrome_binary or ""
    tool.proxy_auto = "" if args.no_proxy else (args.proxy or tool._get_system_proxy())
    tool.manual_image_path = SimpleValue(args.image or "")
    tool.manual_folder_path = SimpleValue(args.folder or "")
    tool.folder_path = args.folder or ""
    tool.proxy_entry = SimpleValue("" if args.no_proxy else (args.proxy or tool.proxy_auto or ""))
    tool.include_subdirs_var = SimpleValue(bool(args.recursive))
    tool.folder_depth_var = SimpleValue(str(args.max_depth))
    tool.log_label = ConsoleLabel()
    tool.status_label = ConsoleLabel()
    tool._refresh_controls = lambda: None
    return tool


def _ensure_cli_driver(tool):
    if tool.driver_path:
        if not os.path.exists(tool.driver_path):
            raise FileNotFoundError(f"指定的ChromeDriver不存在：{tool.driver_path}")
        return tool.driver_path

    existing_driver = tool._find_existing_driver()
    if existing_driver:
        tool.driver_path = existing_driver
        print(f"ChromeDriver：{existing_driver}", flush=True)
        return existing_driver

    detected_driver = tool._download_chromedriver_to_app_dir()
    tool.driver_path = tool._copy_driver_to_app_dir(detected_driver)
    print(f"ChromeDriver：{tool.driver_path}", flush=True)
    return tool.driver_path


def run_cli(args):
    tool = _create_cli_tool(args)
    driver = None
    try:
        driver_path = _ensure_cli_driver(tool)
        if args.download_driver_only:
            print(driver_path)
            return 0

        if args.manual and args.headless:
            print("错误：--manual 需要可见浏览器，不能和 --headless 同时使用", file=sys.stderr)
            return 2
        if args.image and args.folder:
            print("错误：--image 和 --folder 只能选择一个", file=sys.stderr)
            return 2
        if args.manual and args.folder:
            print("错误：--manual 不能和 --folder 同时使用；批量目录模式会自动逐张上传", file=sys.stderr)
            return 2
        if not args.manual and not args.image and not args.folder:
            print("错误：自动模式需要通过 --image 指定图片路径，或通过 --folder 指定图片文件夹", file=sys.stderr)
            return 2
        args.max_results = max(1, min(args.max_results, GoogleImageSearchTool.MAX_RESULTS_LIMIT))
        args.max_depth = max(1, min(args.max_depth, GoogleImageSearchTool.MAX_FOLDER_DEPTH))

        if args.image and not tool._check_image_valid():
            return 2

        proxy = "" if args.no_proxy else (args.proxy or tool.proxy_auto or "")
        driver = tool._init_chrome(driver_path, proxy)

        if args.folder:
            folder_path = Path(args.folder).expanduser().resolve()
            if not folder_path.is_dir():
                print(f"错误：图片文件夹不存在：{folder_path}", file=sys.stderr)
                return 2
            images, skipped = tool._scan_image_files(folder_path, args.recursive, args.max_depth if args.recursive else 1)
            if not images:
                print(f"RESULT_COUNT 0", flush=True)
                print(f"SKIPPED_COUNT {len(skipped)}", flush=True)
                print("错误：文件夹中没有可处理的图片", file=sys.stderr)
                return 1

            records_by_dir = {}
            total_links = 0
            for index, image_path in enumerate(images, 1):
                print(f"PROCESS {index}/{len(images)} {image_path}", flush=True)
                record = {"image": Path(image_path), "links": [], "error": ""}
                try:
                    tool._upload_image(driver, str(image_path))
                    record["links"] = tool._extract_links(driver, args.max_results)
                    total_links += len(record["links"])
                    if args.print_urls:
                        for link in record["links"]:
                            print(f"URL {image_path} {link}", flush=True)
                except Exception as e:
                    record["error"] = str(e)[:300]
                    try:
                        tool._save_debug_files(driver, Path(image_path).parent)
                    except Exception:
                        pass
                    print(f"ERROR {image_path} {record['error']}", flush=True)
                records_by_dir.setdefault(Path(image_path).parent, []).append(record)

            print(f"IMAGE_COUNT {len(images)}", flush=True)
            print(f"RESULT_COUNT {total_links}", flush=True)
            print(f"SKIPPED_COUNT {len(skipped)}", flush=True)

            if not args.no_save:
                paths = tool._save_batch_results(records_by_dir, save_csv=not args.no_csv)
                for path in paths:
                    print(f"SAVED {path}", flush=True)

            if args.keep_browser and sys.stdin.isatty():
                print("浏览器已保留，按 Enter 后关闭。", flush=True)
                input()
            return 0 if total_links else 1

        if args.manual:
            driver.get("https://images.google.com/")
            time.sleep(2)
            tool._dismiss_popups(driver)
            print("请在打开的浏览器中完成上传/验证，然后回到命令行按 Enter 开始提取。", flush=True)
            input()
        else:
            tool._upload_image(driver, tool.image_path)

        links = tool._extract_links(driver, args.max_results)
        print(f"RESULT_COUNT {len(links)}", flush=True)

        if args.print_urls:
            for link in links:
                print(link, flush=True)

        if links and not args.no_save:
            paths = tool._save_links(links, save_csv=not args.no_csv)
            for path in paths:
                print(f"SAVED {path}", flush=True)

        if args.keep_browser and sys.stdin.isatty():
            print("浏览器已保留，按 Enter 后关闭。", flush=True)
            input()

        return 0 if links else 1
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130
    except Exception as e:
        if driver:
            try:
                debug_dir = tool._save_debug_files(driver)
                print(f"调试文件：{debug_dir}", file=sys.stderr)
            except Exception:
                pass
        print(f"错误：{e}", file=sys.stderr)
        return 1
    finally:
        if driver and not args.keep_browser:
            tool._quit_driver(driver)


def build_arg_parser():
    parser = argparse.ArgumentParser(description="谷歌相似图片搜索工具")
    parser.add_argument("--version", action="version", version=f"谷歌相似图片搜索工具 {__version__}")
    parser.add_argument("--cli", action="store_true", help="使用命令行模式；不加该参数时启动图形界面")
    parser.add_argument("-i", "--image", help="要上传搜索的图片路径")
    parser.add_argument("-f", "--folder", help="批量处理的图片文件夹路径；默认只处理当前文件夹")
    parser.add_argument("-n", "--max-results", type=int, default=GoogleImageSearchTool.DEFAULT_MAX_RESULTS, help="最大提取URL数量，默认50")
    parser.add_argument("-o", "--output-dir", help="结果保存目录，默认桌面；没有桌面时保存到程序目录下的output")
    parser.add_argument("--proxy", help="代理地址，例如 http://127.0.0.1:7890 或 127.0.0.1:7890")
    parser.add_argument("--no-proxy", action="store_true", help="禁用自动读取到的系统代理")
    parser.add_argument("--driver", help="手动指定ChromeDriver路径")
    parser.add_argument("--chrome-binary", help="手动指定Chrome/Chromium浏览器路径")
    parser.add_argument("--headless", action="store_true", help="无界面运行Chrome，适合Linux服务器")
    parser.add_argument("--manual", action="store_true", help="打开浏览器后手动上传/验证，再按Enter提取当前页面")
    parser.add_argument("--recursive", action="store_true", help="批量文件夹模式包含子文件夹")
    parser.add_argument("--max-depth", type=int, default=GoogleImageSearchTool.DEFAULT_FOLDER_DEPTH, help="批量递归最大目录层数，默认4；当前文件夹为第1层")
    parser.add_argument("--keep-browser", action="store_true", help="运行结束后保留浏览器；交互终端下按Enter关闭")
    parser.add_argument("--no-csv", action="store_true", help="只保存TXT，不导出CSV")
    parser.add_argument("--no-save", action="store_true", help="不保存文件，只输出数量或URL")
    parser.add_argument("--print-urls", action="store_true", help="在命令行打印提取到的URL")
    parser.add_argument("--download-driver-only", action="store_true", help="只检测/下载ChromeDriver后退出")
    return parser


def run_gui():
    if not TK_AVAILABLE:
        print("错误：当前环境未安装 tkinter，无法启动图形界面；请使用 --cli 命令行模式。", file=sys.stderr)
        return 2

    root = Tk()
    app = GoogleImageSearchTool(root)

    try:
        version = app._get_chrome_version()
        major_ver = int(version.split('.')[0]) if version else 0
        if major_ver and major_ver < 110:
            messagebox.showwarning("版本提示", f"检测到Chrome {major_ver}版，建议升级至110+版本")
    except Exception:
        pass

    root.mainloop()
    return 0


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    raw_args = sys.argv[1:] if argv is None else list(argv)
    cli_executable = "cli" in Path(sys.argv[0]).stem.lower()
    cli_options_used = any([
        args.image, args.folder, args.manual, args.download_driver_only, args.output_dir,
        args.proxy, args.no_proxy, args.driver, args.chrome_binary, args.headless,
        args.keep_browser, args.no_csv, args.no_save, args.print_urls, args.recursive,
    ])

    if cli_executable and not raw_args:
        parser.print_help()
        return 0

    if args.cli or cli_executable or cli_options_used:
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
