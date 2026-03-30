# Yomikomi/Epub2Anki

为你量身定制的 README.md 来了！这份介绍既有极客的专业感，又非常吸引普通日语学习者。
你可以直接将以下内容复制并保存为项目根目录下的 README.md 文件。
📚 YomiKomi (読み込み) - 沉浸式日语轻小说背词神器

- ![alt text](https://img.shields.io/badge/Python-3.8%2B-blue)

- ![alt text](https://img.shields.io/badge/License-MIT-green)

- ![alt text](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey)

YomiKomi 是一款专为日语学习者打造的开源桌面工具。它能将你喜欢的日语轻小说 (EPUB) 与 目标词库 (如 N2/N3 核心词汇) 进行智能碰撞，一键提取小说中出现过的目标单词，并截取小说原句作为例句，最终自动生成 Anki 记忆卡片。
告别死记硬背枯燥的词汇表，在你在喜欢的原著语境中，实现“被电击般”的超强记忆！

 # 核心特性
 精准词汇打击：内置 N1-N3 词库（支持自定义导入 CSV）。只背在你当前阅读的小说中真正出现的单词！
 智能语境截取：自动提取包含生词的完美小说原句，过滤废话与超长句，并在 Anki 卡片中高亮生词。
 外来语杀手 (黑科技)：内置外来语雷达！自动扫描全书片假名，开启多线程并发调用 Jisho + 有道翻译 API，全自动生成带【中英双语】释义的外来语单词卡。
 一键注入 Anki：无缝对接 AnkiConnect 外部 API，点击运行后，卡片瞬间飞入你电脑上的 Anki 软件中。
 多格式自由导出：除了 .apkg，还支持导出排版清爽的 Excel (.csv) 和 纯文本 (.txt)，满足做笔记和打印需求。
 极简现代 UI：基于 CustomTkinter 打造的深色模式原生化操作界面，自带实时多线程滚动日志反馈，拒绝程序假死。
 
 # 快速开始使用
## 方式一：普通用户（小白免安装版）
直接在 [Releases] 页面下载打包好的 YomiKomi.exe（即将发布）。
注意： 运行前请确保将你的词库 CSV 文件放在同级目录的 dicts 文件夹中。
## 方式二：开发者（源码运行）
克隆本项目到本地：
code
Bash
git clone https://github.com/yourusername/YomiKomi.git
cd YomiKomi
安装必备的 Python 依赖库：
code
Bash
pip install customtkinter ebooklib beautifulsoup4 fugashi unidic-lite genanki
运行主程序：
code
Bash
python main.py
# 使用指南
## 1. 准备词汇库 (.csv)
程序自带默认词库，你也可以通过界面上的 [➕ 导入自定义] 按钮导入自己的词库。
自定义词库必须是 UTF-8 或 GBK 编码的 .csv 文件，格式如下（不带表头，以英文逗号分隔）：
code
CSV
黄昏,たそがれ,傍晚
彗星,すいせい,彗星
可愛い,,可爱的 (假名列可留空)
## 2. 配置 Anki（必须）
如果你希望程序能自动将卡片导入 Anki：
打开你的 Anki 电脑端。
点击顶部菜单栏 工具 -> 附加组件 -> 获取附加组件。
输入代码 2055492159 安装 AnkiConnect。
重启 Anki，并保持 Anki 处于打开状态，然后再运行本软件。
## 3. 开始提取
打开 YomiKomi。
选择词库 -> 选择你的轻小说 (.epub)。
勾选你需要的导出格式（推荐勾选“提取外来语”）。
点击 ⚡ 立即提取词汇并导出。
见证奇迹的时刻！
一键打包成 EXE (面向开发者)
如果你修改了源码并想将其打包发给朋友，本项目自带了一键打包脚本，彻底解决 unidic-lite 字典路径丢失的痛点：
确保已安装 PyInstaller：pip install pyinstaller
双击运行目录下的 build.py（或终端运行 python build.py）。
等待 1-3 分钟，打包好的 YomiKomi.exe 会自动生成在 dist 文件夹中！

# 技术栈
GUI 框架: CustomTkinter
日语 NLP 分词: Fugashi + UniDic
EPUB 解析: EbookLib + BeautifulSoup4
Anki 封包:Genanki
API 翻译: Jisho API + 有道翻译 API
并发处理: Python threading & concurrent.futures
🤝 贡献与反馈
如果你在使用过程中遇到了 Bug，或者有更好的点子（比如接入 AI 大模型进行整句翻译），欢迎提交 Issue 或 Pull Request！


