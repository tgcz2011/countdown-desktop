# HANDOFF.md — Countdown Desktop 项目交接文档

> 最后更新: 2026-08-12（v2.0.0.0 Python + CEF 重写）

## 项目概述

Windows 动态壁纸/屏保：网页壁纸（CEF + WorkerW 嵌入）+ 网页屏保（CEF 全屏）。
Python 3.13 + PySide6（仅 QtWidgets）+ 自编译 CEF 渲染进程。

## 版本历史

- **v1.x（Go 版，已废弃）**：Go + WebView2，多轮修复后仍存在嵌入渲染问题，按用户要求重写
- **v2.0.0.0（Python + CEF）**：当前版本。CEF 独立进程渲染，与 Lively 同构

## 环境与工具链

| 工具 | 位置 | 用途 |
|------|------|------|
| Python 3.13 | AutoClaw 自带 `D:\Program Files\AutoClaw\resources\python\python.exe` | 主程序 |
| PySide6 6.11 | pip | 托盘/设置（QtWidgets，**不含** QtWebEngine） |
| PyInstaller | pip | 打包 |
| w64devkit 2.9.1 | `third_party/w64devkit/` | MinGW 编译 helper |
| CEF 3.2704.1414 | `third_party/cef_binary_*/` | Chromium 内核 |
| NSIS 3.12 | `C:\Program Files (x86)\NSIS` | 安装包 |
| 清华 pip 源 | `https://pypi.tuna.tsinghua.edu.cn/simple` | 国内加速 |

## 架构

```
Python 主程序 (CountdownDesktop.exe)
  ├── QSystemTrayIcon（托盘）
  ├── SettingsDialog（设置）
  ├── ScreensaverEngine → CEFEngine → cef_helper.exe（全屏置顶窗口）
  └── WallpaperEngine → CEFEngine → cef_helper.exe（WorkerW 嵌入）
        └── desktop.py: 0x052C(0xD,0x1) → 找壁纸 WorkerW → WS_CHILD → SetParent → 恢复
```

### cef_helper.exe（C++）

- 独立进程渲染（Lively 架构：播放器进程 + 主程序控制）
- 参数：`--url --width --height --x --y [--visible]`
- stdout 输出 `HWND:<hex>` 和 `LOADED:<code>`
- 窗口默认**最小化+屏幕外**创建（壁纸嵌入流程），`--visible` 直接显示（屏保）
- 自定义消息循环：PeekMessage/DispatchMessage + CefDoMessageLoopWork + 500ms NotifyMoveOrResizeStarted
- 编译：`python third_party/build_cef_helper.py`（下载 CEF + MinGW → gendef/dlltool 生成导入库 → 逐文件编译 140 个 .cc → 链接）
- **GCC 16 兼容**：需要 `-fpermissive` + `-include cstring` + 自写 `cef_atomicops_x86_gcc.h`（minimal 包缺 GCC 头）

### 壁纸嵌入流程（Lively 同构，关键！）

1. 检测 raised desktop（Progman 是否 WS_EX_NOREDIRECTIONBITMAP）
2. `SendMessageTimeout(progman, 0x052C, 0xD, 0x1)`（**必须 0xD/0x1**，0,0 无效）
3. 找含 SHELLDLL_DefView 的 WorkerW → **取其下一个 WorkerW 兄弟作为壁纸宿主**（Lively: `FindWindowEx(NULL, tophandle, "WorkerW")`）——**不是 DefView 所在 WorkerW！**
4. helper 窗口：WS_CHILD（手动设！SetParent 不加）→ SetParent(壁纸WorkerW) → SetWindowPos(HWND_BOTTOM, 全屏) → ShowWindow 恢复
5. 嵌入后重发 0x052C（RefreshDesktop）
6. 窗口操作必须在 GUI 线程（Python 主线程即是）

### 屏保

- helper `--visible` 创建 → SetWindowPos(HWND_TOPMOST) → 输入监听（GetLastInputInfo/GetAsyncKeyState 100ms 轮询）→ 任意输入退出
- 空闲检测：5s 轮询，idle >= timeout 启动

## 关键踩坑（血泪史）

### Go 版（v1.x）教训（已废弃但值得记录）
1. GetTickCount 误放 user32 → 5s panic
2. WebView2Loader.dll 不在 System32，需随包分发
3. Go GC 回收 COM 回调对象 → 死锁（需全局持有）
4. 缺 AddRef → controller 悬空崩溃（0xffffffffffffffff）
5. WebView2 需消息泵（GetMessage(0)）+ 创建线程绑定（opCh 调度）
6. SetParent 跨线程静默失败；SetParent 不改 WS_CHILD（必须手动设）
7. DPI 未声明 → 窗口被缩放 1/4（SetProcessDpiAwarenessContext PerMonitorV2）
8. 0x052C 必须 0xD/0x1
9. NSIS 相对路径是脚本目录（需 ..\）；config.json 用 /nonfatal；choco 装的 NSIS 不在 PATH（用完整路径）；OutFile 相对脚本目录
10. 图标：NSIS 拒绝手写 ICO（用 System.Drawing 生成或去掉 MUI_ICON）

### Python + CEF 版（v2.x）
1. **cefpython3 只支持 Python ≤3.7**（死路）→ 自编译 CEF helper
2. **QtWebEngine（PySide6）reparent 后渲染停止**：Qt 6 把 Chromium 内容渲染到独立 Chrome_WidgetWin_0 顶层窗口，嵌入后 Qt 管理冲突 → 弃用
3. **PyQt5 QtWebEngine 在这台机器不渲染**（Chromium 87 太老 + Python 3.13 兼容）
4. **CEF helper 消息循环必须 GetMessage/DispatchMessage**：只 CefDoMessageLoopWork 的话窗口 WM_PAINT 不处理 → 内容渲染了但屏幕不更新（PrintWindow 100% 非黑但屏幕黑）
5. **CEF 最小化创建**：窗口隐藏/最小化时 Chromium 暂停渲染；恢复后需确保消息循环正常
6. **MinGW 链接 MSVC .lib 不行**：gendef + dlltool 从 libcef.dll 生成 .dll.a
7. **CEF minimal 包缺 GCC 原子操作头**（cef_atomicops_x86_gcc.h）：自写（__sync 内建）+ CPU 特性结构
8. **USING_CEF_SHARED 宏**：libcef_dll wrapper 头文件条件编译，缺了类全未声明
9. **NSIS 中文注释报 Bad text encoding**：脚本必须纯 ASCII
10. **PyInstaller 排除 QtWebEngine**：--exclude-module PySide6.QtWebEngine*（省 ~300MB）

## 本机（开发机）验证结论

- 开发机：Windows Server 2022 Datacenter（无 DWM 合成，疑似无影云桌面环境，桌面窗口类含 "CombinedDesktop"）
- **已验证**：CEF 顶层窗口渲染正常（屏保完整显示"距离高考还有"）；壁纸嵌入链路完整（PrintWindow 验证内容 100% 渲染、parent/Z-order/可见性全部正确）
- **本机未验证**：壁纸嵌入的**屏幕显示**（子窗口内容在本机桌面呈现层不合成——云桌面环境限制；PrintWindow 证明渲染本身正常）
- **客户端 Win10/11（有 DWM）**：与 Lively 完全同构的机制，应在客户端正常——**需用户在真实客户端验证**

## 构建与发布

```bash
# 本地构建 helper（首次）
python third_party/build_cef_helper.py

# 打包
python -m PyInstaller --noconfirm --onedir --windowed --name CountdownDesktop run.py
# 复制 third_party/cef_helper/ 运行时到 dist/CountdownDesktop/

# 安装包
& "C:\Program Files (x86)\NSIS\makensis.exe" installer\setup.nsi

# 发布
git tag vX.X.X.X && git push origin vX.X.X.X   # Actions 自动构建 + Release
```

## 版本规则

a.b.c.d：d=修复，c=小功能，b=重要功能，a=架构变更。每次改动（含文档/CI）必须升版本号并同步 README/HANDOFF。

## 已知限制

- 壁纸嵌入屏幕显示需客户端 Win10/11 验证（本机为云桌面环境）
- 安装包较大（~65MB 压缩 / 225MB 安装，Chromium 体积）
- 多显示器未专门处理
- helper 无 IPC（除 stdout HWND）；停止用 TerminateProcess
