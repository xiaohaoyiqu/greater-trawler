# greater-trawler

这里保存“欲求达”开发早期使用过的爬虫参考源码，方便核对旧行为和追溯实现来源。它不是“欲求达”的运行目录，也不作为三个上游项目的替代发布渠道。

## 来源

| 本仓库目录 | 原项目 | 许可证 | 说明 |
| --- | --- | --- | --- |
| `twitter_Crawler/` | [muzi-xiaoren/twitter_Crawler](https://github.com/muzi-xiaoren/twitter_Crawler) | Apache-2.0 | 本地维护版，保留后续稳定性与媒体下载修正 |
| `JMComic-Crawler-Python/` | [hect0x7/JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) | MIT | 本地保存的参考源码快照 |
| `PixivUtil2/` | [Nandaka/PixivUtil2](https://github.com/Nandaka/PixivUtil2) | BSD-2-Clause | 本地保存的参考源码快照 |
| `GoogleImageSearch/` | 项目作者自研 | 未单独声明 | 谷歌图片搜索工具源码与使用文档 |

每个目录仍保留原项目的 `LICENSE` 和说明文档。使用、修改或再分发其中的文件时，以对应目录的许可证为准；需要最新版、问题跟踪或上游文档时，请访问原项目。

## 未收录内容

- Cookie、账号资料、请求头抓包和浏览器配置
- ChromeDriver 等可重新下载的程序
- 图片、视频、音频和其他用户下载内容
- 下载记录、数据库、缓存、IDE 配置和测试输出
- GitHub Actions 工作流

“欲求达”当前源码和文档位于 [xiaohaoyiqu/fast-get-it](https://github.com/xiaohaoyiqu/fast-get-it)，浏览器用户脚本位于 [xiaohaoyiqu/tempermonkey-scripts](https://github.com/xiaohaoyiqu/tempermonkey-scripts)。
