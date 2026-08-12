# Countdown Desktop

Windows 动态壁纸软件：把任意网页设置为**动态壁纸**和**屏幕保护**，默认地址均为 `https://zztool.free.nf/countdown`（高考倒计时页）。

- 动态壁纸：网页窗口嵌入桌面壁纸层（桌面图标之下、原壁纸之上），桌面图标正常可点。
- 屏幕保护：**自绘全屏置顶窗口，不使用系统屏保**；空闲达到设定时长自动触发，任意键鼠输入立即退出，默认 600 秒。
- 壁纸与屏保的 URL **分开设置、均可修改**，互不影响。
- 托盘图标：单击弹出设置；右键菜单含设置、立即启动屏保、刷新壁纸、开机自启、退出。

## 运行环境

- Windows 10 / 11（x64 / ARM64）。
- 依赖 **WebView2 Runtime**（Chromium 内核，保证任意 Win10/11 机器渲染一致）：Win11 与多数 Win10 已预装；若缺失，安装包自动静默安装（内置微软官方 Bootstrapper），无需手动操作。

## 安装与使用

1. 从 [Releases](https://github.com/tgcz2011/countdown-desktop/releases) 下载 `CountdownDesktop_Setup_<版本>.exe` 安装（默认按用户安装，免管理员权限）。
2. 软件常驻托盘。单击托盘或右键 →「设置」：
   - 「动态壁纸」：启用开关 + 壁纸网页 URL；
   - 「屏幕保护」：启用开关 + 屏保网页 URL + 空闲触发时长（秒）；
   - 「保存」后壁纸按新配置立即重启。
3. 「立即启动屏保」可当场预览；按任意键或移动鼠标退出。
4. 「开机自启」写入 HKCU 注册表，登录自动启动（卸载自动清理）。

## 开发与构建

技术栈：Python + PySide6（托盘/设置 UI）+ pywebview（WebView2 渲染）+ Inno Setup 安装包 + GitHub Actions 发布。

```powershell
# 本地一键构建
.\build.ps1 -Version 3.0.0.0

# 或分步
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm CountdownDesktop.spec
& "C:\Program Files\Inno Setup 7\ISCC.exe" /DVERSION=3.0.0.0 installer\setup.iss
```

发布：推送 tag `v<版本>`，GitHub Actions 自动构建安装包并创建 Release。

## 架构速览

```
CountdownDesktop.exe            主进程：托盘/设置/空闲检测/子进程管理
  ├─ run.py player wallpaper    壁纸播放器（WebView2 窗口嵌入 WorkerW/Progman）
  └─ run.py player screensaver  屏保播放器（全屏置顶 + 输入监听退出）
配置 %APPDATA%\CountdownDesktop\config.json；日志同目录 *.log
```

壁纸嵌入参考 [Lively Wallpaper](https://github.com/rocksdanister/lively)：
`SendMessageTimeout(Progman, 0x052C, 0xD, 0x1)` → 定位壁纸宿主（含 `SHELLDLL_DefView` 的 WorkerW 的下一个 WorkerW 兄弟；Win11 raised desktop 时为 Progman 且窗口加 `WS_EX_LAYERED`）→ 转 `WS_CHILD` + `SetParent` → 铺满虚拟屏幕。

## 版本号规则

`a.b.c.d`：d=小改动/修复，c=小添加，b=大改，a=大添加；去掉点后数值严格递增。

## License

GPL-3.0，见 [LICENSE](LICENSE)（架构借鉴 Lively Wallpaper）。
