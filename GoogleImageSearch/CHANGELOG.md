# 更新记录

## v1.1.0 - 2026-07-25

### 新增

- 增加文件夹批量搜索。
- GUI 增加“选择文件夹”“包含子文件夹”“最大层数”“批量搜索文件夹”。
- CLI 增加 `--folder`、`--recursive`、`--max-depth`。
- 批量模式按图片所在目录分别生成 TXT/CSV，并放回对应目录。
- 增加 GIF 文件识别和上传支持。
- 批量扫描会排除非图片、非支持扩展名、超限文件和伪图片文件。

### 规则确认

- 选择目录本身是第 1 层。
- `max-depth=1` 只处理当前目录。
- `max-depth=4` 最多处理 `1(2(3(4)))`，不会进入第 5 层。

### 验证

- 批量扫描层数验证通过。
- 无效 `.jpg` 跳过验证通过。
- CLI 批量模式真实上传测试通过，深度 2 时按当前目录和第 2 层目录分别生成 TXT。

## v1.0.0 - 2026-07-25

当前确认版本。

### 新增

- 增加 Windows 图形界面版和命令行版双入口。
- 增加 CLI 参数：`--image`、`--max-results`、`--output-dir`、`--proxy`、`--no-proxy`、`--driver`、`--chrome-binary`、`--headless`、`--manual`、`--keep-browser`、`--no-csv`、`--no-save`、`--print-urls`、`--download-driver-only`、`--version`。
- 增加 Chrome for Testing 自动下载 ChromeDriver。
- 增加 Linux/macOS 源码运行兼容基础。
- 增加 TXT/CSV 输出。
- 增加失败调试文件输出。
- 增加手动上传后从当前页面提取链接的兜底流程。

### 优化

- 搜索流程改为后台线程，避免 GUI 卡死。
- 移除不必要 import 和原 spec 图标依赖。
- `toollib` 改为运行时懒加载，避免 PyInstaller 扫描无关依赖导致打包失败。
- 增强 Google 结果链接过滤，排除 Google 自有域名和图片直链。
- CLI 自动识别系统代理，并可通过 `--no-proxy` 禁用。

### 验证

- Python 3.10 语法编译通过。
- PyInstaller Windows 打包通过。
- `谷歌图片搜索工具.exe` 和 `谷歌图片搜索工具-cli.exe` 生成成功。
- CLI 使用测试图片完成自动上传、提取和保存。
