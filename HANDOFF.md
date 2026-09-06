# HANDOFF.md — Countdown Desktop 交接文档

> 最后更新: 2026-09-06（v3.2.1.1，修复中考/高考预设模式启动时壁纸不启用）

## 一、需求（用户原始要求）

1. Windows 动态壁纸软件，借鉴 lively（rocksdanister/lively）源码的壁纸嵌入实现。
2. 项目目录 `D:\countdown-desktop`；仓库 `tgcz2011/countdown-desktop`（旧内容完全失败，清空重做）。
3. 网页设为**壁纸**、**屏保**，两者**分开设置、可修改**；默认 URL 均为 `https://zztool.free.nf/countdown`。
4. 屏保默认时长 600s；**不用系统屏保，自写全屏窗口**。
5. NSIS 或 Inno Setup 安装包；**任意 Win10/11 效果一致**（渲染引擎统一为系统 WebView2/Chromium）。
6. 托盘图标调起设置界面，界面不需高级。
7. 语言在 go/rust/python 中选（采用 python + PySide6，用户推荐）。
8. 版本号 `a.b.c.d`（d 小改动、c 小添加、b 大改、a 大添加），去掉点后严格递增；每次更新必须同步更新 README 与 HANDOFF。
9. release 走 GitHub Actions。
10. **v3.2.0.0 追加**：① 倒计时类型切换（高考/中考/自定义；高考=原默认链接 `countdown`，中考=`countdown-junior`）；② 全部设置支持命令行参数单次覆盖（不写入长期配置），主进程透传给播放器子进程；③ 单实例接管：已有实例运行时，新启动的实例（GUI 或带参）自动通知旧实例优雅退出后接管，后启动者覆盖先启动者效果，旧实例无响应时强杀进程树兜底。

## 二、版本历史

| 版本 | 技术 | 结论 |
|------|------|------|
| v1.x | Go + WebView2 | 失败：嵌入渲染/COM 生命周期一连串坑，废弃 |
| v2.0.0.x | Python + 自编译 CEF helper | CI 能过，但 QtWebEngine 路线曾失败、本机壁纸屏幕显示未验证，整体废弃 |
| **v3.0.0.0** | **Python + PySide6 + pywebview(WebView2)** | 本机全链路验证通过 |
| **v3.0.0.1** | 同上 | 修复 CI：中文语言包随仓库分发（d 升） |
| **v3.0.1.2** | 同上 | 壁纸/屏保支持视频/图片/动图（c 升）+ 屏保底部缺口修复（d 升） |
| **v3.1.0.0** | 同上 | 应用图标更换为用户上传的时钟 webp（抠底重建 alpha，多尺寸 ICO/PNG）（b 升）；设置界面改为左侧导航多页结构（壁纸/屏保/通用/关于，页面注册制便于扩展）（b 升）；托盘单击落通用页；自启逻辑统一为 main.set_autostart（设置页与托盘共用，状态互同步）；新增托盘专用白色 glyph 图标 icon-tray（黑托盘可见），读 AppsUseLightTheme 按任务栏主题选图标，WM_SETTINGCHANGE 热切换，浅色任务栏回退彩色主图标 |
| **v3.1.0.1** | 同上 | 修复 v3.1.0.0 启动即崩：主题图标应用被误提前到托盘创建之前（self.tray 不存在 → AttributeError），且构造内仍残留旧名 self.icon 引用；两处修正，图标应用移到 tray.show() 之后（d 升）。教训：测试 Probe 桩绕过了真实 __init__ 顺序，已补 App 真实构造 e2e 测试 |
| **v3.1.1.0** | 同上 | 五项新增/修复（c 升 + b 升）：① 退出/关壁纸后白屏修复——本软件从不改系统壁纸值，退出/停壁纸时把 SPI 当前壁纸原样重设一次强制 explorer 重绘（无快照、无跨进程同步、不回滚用户中途换的壁纸；主进程负责因 terminate 杀进程时 closed 不触发；本机实测 SPI_SET 同路径重设成功）；② 图片/视频画幅可调 cover/contain/fill（壁纸与屏保独立，object-fit 实现）；③ 网页/视频声音可选（默认静音；WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS 合并式追加 autoplay 放行，静音时追加 --mute-audio 覆盖网页源）；④ 视频循环开关（通用页，默认开）；⑤ 设置×按钮显式启用（等同取消）。附带：PyInstaller 6 资源路径修复（_internal/_MEIPASS），frozen 托盘图标此前因此回退系统图标；media.build_html 改 html.escape |
| **v3.1.1.1** | 同上 | 修复 v3.1.1.0 画幅模板 bug（d 升）：fit 样式段用 % 拼接却写了 .format 的 {{}} 转义，浏览器收到非法 CSS 整段丢弃，视频/图片失去铺满样式缩在左上角（网页源不走内联模板不受影响）；改为单花括号，并新增回归测试：禁止 {{ 漏入 HTML、逐 fit/kind 断言 object-fit 规则存在且合法 |
| **v3.1.2.0** | 同上 | 关于页完善（c 升）：新增 GitHub 仓库/反馈链接、GPL-3.0 许可说明、Lively Wallpaper（rocksdanister）鸣谢；新增检查更新（GitHub Releases API，去点数值比较）+ 一键更新（下载安装包到 %TEMP%，批处理 taskkill 后 Inno /SILENT /RESTARTAPPLICATIONS 静默装并重启）+ 启动自动检查（仅提示不自动下载，可关）；新模块 app/update.py（QNetworkAccessManager 异步，信号驱动） |
| **v3.2.0.0** | 同上 | 中高考切换 + 命令行参数（c 升 + c 升）：①「倒计时」设置页：高考/中考/自定义三态（高考=原默认 `countdown`，中考=`countdown-junior`；预设模式壁纸/屏保统一用预设地址且输入框只读，自定义模式两者分别可填）；config 新增 exam_type，旧版配置无该字段时按存量 URL 推断迁移（双高考→gaokao、双中考→zhongkao、其余→custom，升级前后行为一致）；② 新模块 app/cli.py：全部设置可通过 `--exam/--wallpaper-url/--screensaver-timeout/--video-loop…` 等参数单次覆盖（仅内存不落盘），主进程 _spawn_cmd 把参数透传给播放器子进程、refresh_wallpaper 重新套用；--help 弹窗显示用法；未知参数弹窗警告并忽略；③ 单实例接管：命名互斥量 CountdownDesktop_Single + 命名事件 CountdownDesktop_Quit（250ms 轮询）+ PID 文件 main.pid；新实例检测到互斥量被占时 SetEvent 通知旧实例 quit()（优雅：停壁纸/恢复桌面/删 pid/退托盘），5s 未退则 taskkill /F /T 强杀进程树，然后接管；GUI↔CLI 可互相接管；④ 单实例检查移到 QApplication 创建之后（消息弹窗依赖 qapp）；⑤ 新增 tools/test_cli.py 回归测试（解析/序列化/覆盖/migration），tools/test_takeover.py 端到端接管测试，test_settings.py 改为隔离临时配置目录防污染 |
| **v3.2.1.0** | 同上 | 新增 --quit 优雅退出命令（c 升）：run() 在创建 QApplication 之前检测 --quit，调用模块级 quit_running_instance()——检测互斥量判断是否有实例运行→SetEvent 通知优雅退出（5s）→超时 taskkill /F /T 强杀（3s）→返回退出码（0=成功/无实例，1=失败）；不启动 GUI、不创建托盘，供其他软件/脚本/任务计划调用；无实例时幂等返回 0。新增 tools/test_quit.py 端到端测试（有实例优雅退出+无实例幂等） |
| **v3.2.1.1** | 同上 | 修复中考/高考预设模式启动时壁纸不启用（d 升）：根因是 cli.apply 只改 exam_type 和 URL，不触碰 wallpaper/screensaver 的 enabled 字段——若用户此前关闭过壁纸（enabled=False），用 `--exam zhongkao` 或设置界面切到中考后，URL 已换成 countdown-junior 但 enabled 仍为 False，导致壁纸进程根本不 spawn。修复：① cli.apply 中显式 `--exam gaokao/zhongkao` 时自动把 wallpaper.enabled 和 screensaver.enabled 置 True（预设模式的核心用途就是显示倒计时）；显式 `--wallpaper-enabled off` 仍优先，尊重用户主动关闭。② 设置界面 _on_exam_changed 新增 auto_enable 参数：用户手动切到高考/中考时自动勾选两个启用框，load_all 同步时传 auto_enable=False 不覆盖已保存状态。回归测试覆盖 5 种场景（zhongkao/gaokao 自动启用、custom 不自动启用、无参保持原状态、显式 off 优先） |

## 三、架构

```
CountdownDesktop.exe（主进程）
  ├─ QSystemTrayIcon（单击=设置；菜单：设置/立即启动屏保/刷新壁纸/开机自启/退出）
  ├─ QTimer 5s 空闲检测（GetLastInputInfo）→ 超时 spawn 屏保播放器
  └─ 启动时 spawn 壁纸播放器
run.py player wallpaper   → pywebview 窗口 → WorkerW/Progman 嵌入（Lively 同构）
run.py player screensaver → pywebview 窗口 → 全屏 TOPMOST + 隐藏任务栏/光标 + 输入即退
配置：%APPDATA%\CountdownDesktop\config.json
日志：%APPDATA%\CountdownDesktop\{main,player-wallpaper,player-screensaver}.log
命令行覆盖：app/cli.py（主进程与播放器子进程共用；_spawn_cmd 透传 serialize 结果）
单实例接管：互斥量 CountdownDesktop_Single + 命名事件 CountdownDesktop_Quit（250ms 轮询）+ PID 文件；新实例 SetEvent→旧实例 quit()，5s 超时 taskkill /F /T 兜底
--quit 退出命令：run() 早于 QApplication 检测 → quit_running_instance()（SetEvent+等待+强杀兜底），不启动 GUI，退出码 0/1


> 注：本文件中「云桌面抓不到壁纸层」类限制均为开发机 Windows Server 2022 云桌面特有环境问题，常规 Win10/11 物理机不受影响。
```

壁纸嵌入序列（app/win32.py，继承自旧版血泪史并复验）：
1. `SendMessageTimeout(Progman, 0x052C, 0xD, 0x1)`（**0,0 无效**）
2. 宿主定位：含 `SHELLDLL_DefView` 的顶层 WorkerW 的**下一个 WorkerW 兄弟**；
   DefView 直接在 Progman 下或 Progman 带 `WS_EX_NOREDIRECTIONBITMAP`（Win11 raised desktop）时宿主=Progman，壁纸窗口加 `WS_EX_LAYERED + alpha=255`
3. 去 `WS_POPUP/OVERLAPPED`、加 `WS_CHILD|WS_VISIBLE`（**SetParent 不自动加 WS_CHILD**）
4. `SetParent(host)` → `SetWindowPos(HWND_BOTTOM, 虚拟全屏)` → `ShowWindow(SW_SHOWNA)`
5. 窗口操作与创建同线程；`SetWindowLongPtrW` 的值要转**有符号 32 位**（否则 ctypes OverflowError）

## 四、踩过的错误 / 经验（含旧版继承）

### 渲染引擎选型（最重要）
1. **QtWebEngine reparent 后渲染停止**：Qt6 把 Chromium 内容渲染到独立 `Chrome_WidgetWin_0` 顶层窗口，嵌入后容器空白。v2 因此弃用；v3 用 Qt 6.11 再次验证仍然如此（PrintWindow 容器空白、Chrome_WidgetWin_0 仍是顶层窗口）。**结论：QtWebEngine 永远不能用于嵌入壁纸**。
2. **pywebview edgechromium（WebView2）SetParent 后渲染正常**：WebView2 控件（`Chrome_WidgetWin_1` 等）是 pywebview 窗口的**子窗口**，随父窗口一起被嵌入/置顶。已用 `PrintWindow(hwnd, dc, PW_RENDERFULLCONTENT=2)` 截图实证网页倒计时画面在桌面壁纸层内。
3. 开发机（Windows Server 2022 云桌面，无常规桌面壁纸层）`ImageGrab.grab` 抓不到壁纸层内容——**此为该云桌面特有环境限制，常规 Win10/11 物理机无此问题**；但验证习惯仍推荐 `tools/capture.py`（PrintWindow PW_RENDERFULLCONTENT 抓宿主窗口），比全屏截图更精准。

### Win32 嵌入
4. 0x052C 必须 `0xD,0x1`；壁纸宿主是 DefView WorkerW 的下一个兄弟，**不是 DefView 所在那个**。
5. `SetParent` 前手动 `WS_CHILD`；raised desktop 要 `WS_EX_LAYERED+SetLayeredWindowAttributes(255)`，否则不绘制。
6. ctypes：`SetWindowLongPtrW` 样式值需 to_signed32；`restype/argtypes` 别写反（曾把 argtypes 写成 restype 直接 TypeError）。

### 打包/安装包
7. PyInstaller 6.x：`PYZ(a.pure)`（无 `a.zlib_data` 属性）。
8. 本机 Inno Setup 装在 `C:\Program Files\Inno Setup 7\ISCC.exe`（不在 x86/6 常规路径，Test-Path 要全找）；CI 的 windows-latest 自带 Inno 6（路径 `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`）。
9. iss 脚本**纯 ASCII**（中文注释/描述易出编码问题）；界面语言用 `ChineseSimplified.isl`。
10. 任意 Win10 兼容：安装包内置微软官方 `MicrosoftEdgeWebview2Setup.exe`（Bootstrapper，~1.7MB， Evergreen 在线安装），安装时检测注册表 `{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` 的 `pv`，缺失则 `/silent /install`。Win11 预装 WebView2 无需触发。
11. 免管理员：`PrivilegesRequired=lowest`（用户目录安装），开机自启用 HKCU Run（卸载 `uninsdeletevalue` 清理）。
12. WebView2 用户数据目录（`%APPDATA%\<app>\*.WebView2`）不要打包/提交。

### 旧版教训（仍适用，保留）
13. DPI：创建窗口前 `SetProcessDpiAwarenessContext(PER_MONITOR_V2)`，否则窗口缩放。
14. `GetLastInputInfo` 的 GetTickCount 32 位回绕要掩码处理。
15. NSIS 相关坑已随 NSIS 脚本一起废弃（v3 用 Inno）。
16. CI 里所有本地手动补丁必须进仓库/构建脚本，否则 CI 复现失败（v2.0.0.1 教训）。
17. **CI 的 windows-latest 自带 Inno 6 不含 `ChineseSimplified.isl`**（官方精简发行不带语言包）→ 语言包文件 `installer/ChineseSimplified.isl` 必须随仓库分发，`[Languages]` 用相对路径引用。v3.0.0.1 修复。
18. **屏保全屏夹边**：pywebview/Qt 窗口 `SetWindowPos` 全屏会被系统夹到工作区附近（实测 3824x1707 vs 虚拟屏 3840x1746，底部露壁纸）；外部 SetWindowPos/去边框样式都无效，唯一有效是 `ShowWindow(SW_SHOWMAXIMIZED)`（隐藏任务栏后按整显示器计算）。顺序：隐藏任务栏 → maximize → SetWindowPos TOPMOST 双保险。v3.0.1.2 修复。
19. **验证前必须清残留壁纸进程**：旧壁纸窗口挂在宿主上层会遮住新窗口，抓图看到旧内容误判为新功能失败。测试媒体类型前先 `Get-Process CountdownDesktop/python player` 全清。
20. **本地媒体文件必须走 127.0.0.1 HTTP**：WebView2 默认禁 file:// 访问；app/media.py 的 LocalSource（ThreadingHTTPServer + Range 支持）保活在播放器进程内。
21. **源无效必须回退默认网页**：配置指向已删除的本地文件会黑屏（`D:\...` 被补成 https 域名也打不开）；media.resolve 对路径样式但文件不存在的源回退 `config.DEFAULT_URL`。
22. **build.ps1 在 PS 5.1 下不能用 `$ErrorActionPreference="Stop"`**：原生 exe 的 stderr INFO 行（PyInstaller/ISCC 都有）会变终止错误；改 Continue + 检查 `$LASTEXITCODE`（Invoke-Step）。
23. 验证机长期无人输入：主程序启动 600s 后屏保会自动触发，属正常产品行为，验证壁纸时注意区分（抓图看到黑顶=屏保盖在上面）。
24. **设置类测试必须隔离真实配置**（v3.2.0.0 教训）：test_settings 曾直接 `config.load/save` 真实 `%APPDATA%\CountdownDesktop\config.json`，覆盖了用户自定义源地址。任何会 save 的测试都要先 `config.config_dir = lambda: 临时目录`（test_cli/test_settings 均如此），并确认真实配置文件未被改动。
25. 本机 APPDATA 配置曾被人为/实验性改动（壁纸=本地 mp4、屏保=example.com/x、D:\countdown-desktop 曾含 --url 实验副本且已删除）：改前先核对 config 与日志时间线，不要假设默认值。
26. **跨进程 IPC 不要用 QLocalServer/QLocalSocket**（v3.2.0.0 教训）：同进程内正常，跨进程时客户端 connect/write 成功但服务端 newConnection 不触发（PySide6 6.11 + Windows 命名管道已知坑）。单实例接管改用 Win32 命名事件（CreateEventW/OpenEventW/SetEvent + 250ms 轮询 WaitForSingleObject），简单可靠；强杀兜底用 taskkill /F /T /PID（PID 文件在 config_dir/main.pid）。

## 五、项目结构

```
countdown-desktop/
├── run.py                  入口（无参=主程序；player <mode>=播放器）
├── app/
│   ├── main.py             主进程：托盘/空闲检测/子进程管理/单实例互斥量+命名事件接管（v3.2.0.0）
│   ├── player.py           播放器：壁纸嵌入/屏保全屏/输入退出/隐藏任务栏
│   ├── win32.py            Win32 封装（嵌入/全屏/空闲/自启/mutex/DPI）
│   ├── settings.py         设置对话框（左侧导航多页：倒计时/壁纸/屏保/通用/关于；页面注册制 PAGES）
│   ├── cli.py              命令行参数解析/覆盖应用/子进程透传序列化（v3.2.0.0 新增）
│   ├── config.py           config.json 读写（倒计时预设 URL + exam_type 迁移 + 600s）
│   ├── media.py            媒体源：类型识别/本地文件 HTTP 服务/视频图片渲染页
│   └── version.py          版本号（唯一来源之一，供 build.ps1 读取）
├── assets/icon.ico         多尺寸 ICO（256/128/64/48/32/24/16，新时钟图标）
├── assets/icon.png         256px 打底 PNG（同一时钟图标）
├── assets/icon-tray.ico    托盘专用白色描边 glyph（256…16 八尺寸，黑托盘可见）
├── assets/icon-tray.png    256px 白 glyph PNG（同一托盘图标）
├── installer/
│   ├── setup.iss           Inno 安装脚本（内置 WebView2 bootstrapper 检测安装）
│   └── MicrosoftEdgeWebview2Setup.exe
├── tools/capture.py        开发验证截图（PrintWindow fullcontent）
├── tools/test_cli.py       命令行参数/覆盖/迁移回归测试（v3.2.0.0 新增，无需 GUI）
├── tools/test_takeover.py  单实例接管端到端测试（v3.2.0.0 新增，启动两个真实进程验证）
├── tools/test_quit.py      --quit 优雅退出命令端到端测试（v3.2.1.0 新增）
├── tools/test_settings.py  设置界面渲染/保存测试（隔离临时配置目录）
├── build.ps1               本地一键构建
├── CountdownDesktop.spec   PyInstaller 规格
├── requirements.txt        PySide6 + pywebview
├── .github/workflows/release.yml   tag→构建→Inno→Release
├── README.md / HANDOFF.md  （每次更新强制同步）
```

## 六、toolchain

| 工具 | 位置/版本 | 说明 |
|------|-----------|------|
| Python | 开发机 3.14（venv 于 `.venv`）；CI 用 3.12 | pywebview 官方 wheel 覆盖 3.12；3.14 本机实测可用 |
| PySide6 | 6.11 | 仅 Widgets/Gui/Core（托盘+设置），**不用 QtWebEngine** |
| pywebview | 6.2 | EdgeChromium 后端 |
| PyInstaller | 6.22 | onedir |
| Inno Setup | 本机 7（`C:\Program Files\Inno Setup 7`）；CI 6 | ISCC 编译 |
| git/gh | 已登录 tgcz2011 | 推送与 release |
| GitHub Actions | windows-latest | 自动构建发布 |
| pip 源 | 清华 | 国内加速 |

## 七、构建与发布

```powershell
# 本地
.\build.ps1 -Version 3.0.1.2        # venv+pip+PyInstaller+ISCC 一条龙

# 发布
git add -A; git commit -m "..."
git tag v3.0.1.2; git push origin main v3.0.1.2   # Actions 自动 Release
```

## 八、版本规则

a=大添加 b=大改 c=小添加 d=小改动；去掉 `.` 后数值必须严格大于上一版本。当前最高已发布 tag：v3.2.1.1（历史 v1/v2 tag 已废弃但保留）。

## 八·一、图标更换记录（v3.1.0.0）

- 源：用户上传 800x800 webp（深色圆环时钟、白色系棋盘格底被烧进像素，RGB 无 alpha）。
- 泛洪抠图失败：圆形内切画布，四边中点处圆环紧贴图像边缘，边缘种子点落在深色环上把环咬掉。
- 最终方案：白色系像素归一化（阈值 235 去棋盘残影）+ 几何圆形 alpha（4x 超采样，圆心 (400,400) 半径 400）。
- 产物：assets/icon.png（256 打底，内容 92% 留 padding）、assets/icon.ico（256/128/64/48/32/24/16 七尺寸）。
- 托盘可见性（v3.1.0.0 追加）：主图标深色在默认黑托盘不可见 → 另建 icon-tray.ico 白色描边 glyph
  （深色像素软阈值 90/150 抽成蒙版转白，表盘镂空）；运行时读 HKCU AppsUseLightTheme，
  深色任务栏用白 glyph、浅色回退彩色 icon.ico，WM_SETTINGCHANGE(ImmersiveColorSet) 热切换；
  icon-tray.ico 已加入 PyInstaller datas。
- 引用点：PyInstaller spec（datas + EXE icon）、Inno SetupIconFile、main.py 托盘 QIcon —— 均无需改路径。
- 重建脚本：.openclaw/tmp/icon-work/build_icon.py（workspace，不入库）。

## 九、已知限制 / 待办

1. explorer 重启后壁纸需手动「刷新壁纸」（未做自动监控恢复；lively 旧版也没有）。
2. 多显示器按虚拟屏幕整块铺满（span 模式），未做每屏独立窗口。
3. 屏保触发检测粒度 5s；启动后 1s 内输入不触发退出（防误触）。
4. WebView2 版本随系统更新，极老 Win10 需联网装 runtime（安装包装）。
5. 开发机（Windows Server 2022 云桌面）`ImageGrab` 抓屏不含壁纸层——**云桌面特有限制，非普遍问题**；常规 Win10/11 客户端壁纸层显示按 Lively 同构机制实现。

## 十、验证方法备忘

```powershell
# 抓桌面宿主窗口（看壁纸是否在壁纸层渲染）
.\.venv\Scripts\python.exe tools\capture.py out.png host
# 全屏截图（屏保验证可用；壁纸层抓取在 Windows Server 2022 云桌面受限，物理机不受限）
.\.venv\Scripts\python.exe tools\capture.py out.png screen
```

屏保退出验证：`keybd_event` 模拟按键后确认 player-screensaver 进程退出。
