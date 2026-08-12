# HANDOFF.md — Countdown Desktop 交接文档

> 最后更新: 2026-08-12（v3.0.1.2，媒体类型支持 + 屏保全屏修复）

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

## 二、版本历史

| 版本 | 技术 | 结论 |
|------|------|------|
| v1.x | Go + WebView2 | 失败：嵌入渲染/COM 生命周期一连串坑，废弃 |
| v2.0.0.x | Python + 自编译 CEF helper | CI 能过，但 QtWebEngine 路线曾失败、本机壁纸屏幕显示未验证，整体废弃 |
| **v3.0.0.0** | **Python + PySide6 + pywebview(WebView2)** | 本机全链路验证通过 |
| **v3.0.0.1** | 同上 | 修复 CI：中文语言包随仓库分发（d 升） |
| **v3.0.1.2** | 同上 | 壁纸/屏保支持视频/图片/动图（c 升）+ 屏保底部缺口修复（d 升） |

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
3. 开发机（Windows Server 2022 云桌面）`ImageGrab.grab` 抓不到壁纸层内容，**验证一律用 `tools/capture.py`（PrintWindow PW_RENDERFULLCONTENT）抓宿主窗口**，别用全屏截图下结论。

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

## 五、项目结构

```
countdown-desktop/
├── run.py                  入口（无参=主程序；player <mode>=播放器）
├── app/
│   ├── main.py             主进程：托盘/空闲检测/子进程管理/单实例 mutex
│   ├── player.py           播放器：壁纸嵌入/屏保全屏/输入退出/隐藏任务栏
│   ├── win32.py            Win32 封装（嵌入/全屏/空闲/自启/mutex/DPI）
│   ├── settings.py         设置对话框（壁纸与屏保分开设）
│   ├── config.py           config.json 读写（默认 URL + 600s）
│   ├── media.py            媒体源：类型识别/本地文件 HTTP 服务/视频图片渲染页
│   └── version.py          版本号（唯一来源之一，供 build.ps1 读取）
├── assets/icon.ico
├── installer/
│   ├── setup.iss           Inno 安装脚本（内置 WebView2 bootstrapper 检测安装）
│   └── MicrosoftEdgeWebview2Setup.exe
├── tools/capture.py        开发验证截图（PrintWindow fullcontent）
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

a=大添加 b=大改 c=小添加 d=小改动；去掉 `.` 后数值必须严格大于上一版本。当前最高 tag：v3.0.1.2（历史 v1/v2 tag 已废弃但保留）。

## 九、已知限制 / 待办

1. explorer 重启后壁纸需手动「刷新壁纸」（未做自动监控恢复；lively 旧版也没有）。
2. 多显示器按虚拟屏幕整块铺满（span 模式），未做每屏独立窗口。
3. 屏保触发检测粒度 5s；启动后 1s 内输入不触发退出（防误触）。
4. WebView2 版本随系统更新，极老 Win10 需联网装 runtime（安装包装）。
5. 开发机为云桌面，`ImageGrab` 抓屏不含壁纸层；真机客户端（Win10/11 常规环境）显示已按 Lively 同构机制实现，建议真机复验。

## 十、验证方法备忘

```powershell
# 抓桌面宿主窗口（看壁纸是否在壁纸层渲染）
.\.venv\Scripts\python.exe tools\capture.py out.png host
# 全屏截图（屏保验证可用，壁纸层在云桌面抓不到）
.\.venv\Scripts\python.exe tools\capture.py out.png screen
```

屏保退出验证：`keybd_event` 模拟按键后确认 player-screensaver 进程退出。
