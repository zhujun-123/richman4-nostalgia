# 大富翁4 · 怀旧版

以原版画面、人物、地图、动画、音乐、语音和传统玩法为还原目标的非官方原生移植。适合在自己的 Mac 上学习和体验。

本仓库是 [lhr0909/richman4-remastered](https://github.com/lhr0909/richman4-remastered) 的独立 fork，基于其原生 C++20 / SDL3 引擎；上游格式与规则研究来自 [mytbk/rich4](https://github.com/mytbk/rich4)。保留完整提交历史及 GPL-3.0-or-later 许可证。它与 [MIT 原创学习版](https://github.com/zhujun-123/richman-holiday) 是两个独立项目。

**“一比一”是验收目标，当前不宣称已经达到 100% 还原。** 本仓库尚未接入用户的原版素材，原版画面、音频和完整对局仍待实机验证。已知差异与本仓库验证记录见 [怀旧版状态](docs/NOSTALGIA_STATUS.md)；上游平台与功能说明保留在 [README.upstream.md](README.upstream.md)。

## 在 Mac 上启动

1. 准备自己拥有的《大富翁4》游戏目录。官方发行页：[Steam 大富翁4](https://store.steampowered.com/app/2059810/?l=schinese)。原版资源不包含在本仓库中。
2. 安装构建依赖（首次需要）：

   ~~~sh
   brew install cmake sdl3 freetype fluid-synth pkgconf
   ~~~

3. 在仓库根目录运行一次：

   ~~~sh
   python3 scripts/nostalgia.py setup "/你的大富翁4游戏目录"
   ~~~

   目录中应直接包含 Data.mkf、Panel.mkf、map.mkf、Effect.mkf、Speaking.mkf、jump.mkf、help.mkf 以及原版 MIDI 音乐。支持文件名大小写不同、中文路径和空格。脚本只记录本机路径，不复制或改写原版文件；本机配置位于已忽略的 .local/nostalgia.json。

4. 双击根目录的 **启动怀旧版.command**，或运行：

   ~~~sh
   python3 scripts/nostalgia.py play
   ~~~

启动时先检查素材，再构建本机程序。空格 / Enter 掷骰，F5 存档，F9 读档。存档保存在 ~/Library/Application Support/Rich4Nostalgia/saves；运行日志位于 artifacts/nostalgia-runtime.log。

字体优先使用本机已有的细明体。没有时使用系统中文字体，并明确提示字形差异；可通过 play --font "/本机字体路径" 指定。不会下载或打包商业字体。

只读检查素材：

~~~sh
python3 scripts/nostalgia.py check
python3 scripts/nostalgia.py check --assets "/其他游戏目录" --json
~~~

素材不完整时，启动入口会停止并列出缺少文件。素材包的边界检查不代表完整解码或游戏体验验收。

## 没有素材也能编译与学习

只构建 Mac 游戏程序：

~~~sh
python3 scripts/nostalgia.py build
~~~

编译规则核心并运行不依赖商业素材的测试：

~~~sh
cmake -S . -B build/core -DCMAKE_BUILD_TYPE=Debug -DRICH4_SANITIZERS=ON -DRICH4_BUILD_VIEWER=OFF -DRICH4_BUILD_GAME=OFF
cmake --build build/core --parallel 4
ctest --test-dir build/core --output-on-failure
~~~

GitHub Actions 在 macOS 与 Linux 上执行这组核心测试。测试使用生成的数据；通过不等于完成原版界面或声音的验收。

## 代码入口

- src/、include/rich4/：资源格式、地图、地产、银行、股市、卡片、道具、神明与回合规则。
- tools/native_game.cpp、tools/screens/：SDL3 游戏主循环及原版各个界面。
- scripts/nostalgia.py：本 fork 的中文素材检查、配置和 Mac 启动入口。
- docs/ui/、docs/migrations/：上游的原版界面和规则研究记录。
- tests/：核心行为与启动入口测试。

## 来源与许可

本 fork 保留 [Simon Liang 的上游移植](https://github.com/lhr0909/richman4-remastered) 及 [Iru Cai 等人的逆向研究](https://github.com/mytbk/rich4) 的贡献记录；基线提交为 3f4209a7dfb5b2f20799bf54e6c03c5faa11c557。本次增加本机素材配置、中文启动流程、独立存档目录与自动测试；没有重新署名上游引擎。

引擎及衍生代码按 **GPL-3.0-or-later** 授权，不能把这份衍生实现改为 MIT。原版游戏内容的权利仍属于 SOFTSTAR 等权利人，未获本仓库许可证授权。素材和含素材的本机构建产物不提交到仓库。详情见 [LICENSE](LICENSE)、[NOTICE.md](NOTICE.md) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
