# 谷歌相似图片搜索工具

当前版本：v1.1.0

这是一个基于 Selenium + Chrome/ChromeDriver 的 Google 相似图片搜索工具。它可以上传本地图片到 Google 图片/Google Lens，提取结果页面里的外部来源 URL，并导出为 TXT/CSV。

## 已确认功能

- Windows 图形界面使用。
- Windows 命令行使用。
- Linux/macOS 源码命令行运行基础兼容。
- 单张图片搜索。
- 文件夹批量搜索。
- 批量模式可选择只处理当前目录，或递归处理子目录。
- 批量递归可设置最大目录层数，默认 4 层，最高 8 层。
- 批量模式按图片所在目录分别生成结果文件，并放回对应目录。
- 自动检测或下载 ChromeDriver 到程序同级目录。
- 支持手动指定 ChromeDriver 和 Chrome/Chromium 路径。
- 支持 JPG / JPEG / PNG / WEBP / GIF，排除其他格式和无效图片文件。
- 支持最大提取数量限制，范围 1-500。
- 支持 TXT 和 CSV 输出。
- 支持代理、禁用系统代理、headless 运行。
- 搜索失败时保存页面 HTML、截图和异常日志用于调试。

## Windows 使用

打包后 `dist` 目录有两个可执行文件：

- `谷歌图片搜索工具.exe`：图形界面版，双击使用。
- `谷歌图片搜索工具-cli.exe`：命令行版，适合批处理和自动化任务。

单图命令行示例：

```powershell
.\谷歌图片搜索工具-cli.exe --image "D:\images\test.png" --max-results 50 --output-dir .\result --no-proxy
```

批量处理当前文件夹，不进入子目录：

```powershell
.\谷歌图片搜索工具-cli.exe --folder "D:\images" --max-results 20 --no-proxy
```

批量处理当前文件夹和子目录，最多进入 4 层目录：

```powershell
.\谷歌图片搜索工具-cli.exe --folder "D:\images" --recursive --max-depth 4 --max-results 20 --no-proxy
```

## 目录层数定义

选择的文件夹本身是第 1 层。

- `--max-depth 1`：只处理当前文件夹。
- `--max-depth 2`：处理当前文件夹和直接子文件夹。
- `--max-depth 4`：处理 `1(2(3(4)))`，不会进入第 5 层。

GUI 中不勾选“包含子文件夹”等同于只处理第 1 层。

## 批量输出规则

批量模式会按图片所在目录分别生成结果文件：

- 当前文件夹中的图片：结果文件放在当前文件夹。
- 子文件夹中的图片：结果文件放在对应子文件夹。

文件名：

- `谷歌图片批量搜索结果_YYYYMMDD_HHMMSS.txt`
- `谷歌图片批量搜索结果_YYYYMMDD_HHMMSS.csv`

CSV 行字段包含图片名、图片路径、状态、URL 和错误信息。

## Linux 源码运行

要求：Python 3.10+、Chrome 或 Chromium、可访问 Google 的网络。

```bash
python3.10 -m pip install -r requirements.txt
python3.10 googlesearchpicture.py --folder ./images --recursive --max-depth 4 --headless --no-proxy
```

如果浏览器不在常见路径：

```bash
python3.10 googlesearchpicture.py --image ./test.png --headless --chrome-binary /usr/bin/chromium
```

Linux 图形界面需要 tkinter 和桌面环境；服务器环境建议使用 `--headless`。

## 常用命令

查看版本：

```powershell
.\谷歌图片搜索工具-cli.exe --version
```

只下载或检测 ChromeDriver：

```powershell
.\谷歌图片搜索工具-cli.exe --download-driver-only
```

打印 URL，不保存文件：

```powershell
.\谷歌图片搜索工具-cli.exe --image "D:\images\test.png" --print-urls --no-save --no-proxy
```

手动模式：

```powershell
.\谷歌图片搜索工具-cli.exe --manual --max-results 50
```

## 兼容说明

- Chrome 和 ChromeDriver 主版本需要匹配；工具会通过 Chrome for Testing 自动匹配下载。
- Google 页面可能改版，自动上传或提取失败时优先使用手动模式。
- 某些系统代理可能是无效占位值，连接超时时可尝试 `--no-proxy`。
- Windows 上打包出的 exe 只能用于 Windows；Linux 版可执行文件需要在 Linux 上重新打包。
- 当前工具提取的是结果页面中的外部来源 URL，不下载图片本体。