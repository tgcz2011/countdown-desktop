# -*- coding: utf-8 -*-
"""检查更新：GitHub Releases API 查询 + Qt 后台下载 + 静默安装重启。

流程：
  check()     异步请求 releases/latest，去点数值比较（与项目版本规则一致）
  download()  二次请求 release JSON 拿安装包资产 URL，流式下载到 %TEMP%
  install()   生成批处理：taskkill 本程序 → 静默安装（Inno /SILENT 等）→ 重启；
              调用方随后退出主程序，退出即更新。

全部走 QNetworkAccessManager 异步，不卡设置窗口 UI。
"""
import json
import logging
import os
import re
import subprocess
import sys
import tempfile

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                               QNetworkRequest)

log = logging.getLogger("update")

REPO_OWNER = "tgcz2011"
REPO_NAME = "countdown-desktop"
REPO_PAGE = "https://github.com/%s/%s" % (REPO_OWNER, REPO_NAME)
REPO_API = "https://api.github.com/repos/%s/%s/releases/latest" % (REPO_OWNER, REPO_NAME)
ASSET_RE = re.compile(r"\.exe$", re.I)
UA = "CountdownDesktop-Updater"
MIN_INSTALLER_BYTES = 1 << 20  # 安装包约 37MB，小于 1MB 视为被拦截/损坏


def _to_num(v: str) -> int:
    """3.1.1.1 -> 3111（与项目 a.b.c.d 去点严格递增规则一致）。"""
    parts = [p for p in v.strip().lstrip("vV").split(".") if p.isdigit()]
    return int("".join(parts)) if parts else 0


def is_newer(remote: str, local: str) -> bool:
    return _to_num(remote) > _to_num(local)


class UpdateChecker(QObject):
    """关于页更新组件。信号驱动，设置窗口关闭即随对象树销毁，无泄漏。"""

    checkFinished = Signal(bool, str, str)  # (有更新, 最新版本, 更新说明/错误)
    downloadProgress = Signal(int, int)     # (received, total)
    downloadFinished = Signal(bool, str)    # (成功, 安装包路径/错误)
    installPrepared = Signal(str)           # (bat 路径)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self._on_finished)
        self._phase = "idle"  # idle / check / meta / asset
        self._latest = ""
        self._reply = None
        self._fh = None
        self._file_path = ""

    # ---------------- 公共动作 ----------------
    def check(self) -> None:
        self._phase = "check"
        self.nam.get(self._req(REPO_API))

    def download(self) -> None:
        """先拉 release 元数据拿资产 URL（下载按钮按下时才联网）。"""
        if not self._latest:
            self.downloadFinished.emit(False, "请先检查更新")
            return
        self._phase = "meta"
        self.nam.get(self._req(REPO_API))

    def cancel(self) -> None:
        if self._reply is not None:
            self._reply.abort()

    # ---------------- 内部 ----------------
    @staticmethod
    def _req(url: str) -> QNetworkRequest:
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.UserAgentHeader, UA)
        req.setRawHeader(b"Accept", b"application/vnd.github+json")
        req.setAttribute(QNetworkRequest.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        return req

    def _fail(self, msg: str) -> None:
        if self._phase in ("check", "meta"):
            self.checkFinished.emit(False, "", msg)
        else:
            self.downloadFinished.emit(False, msg)
        self._cleanup()

    def _cleanup(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None
        self._phase = "idle"

    def _on_finished(self, reply: QNetworkReply) -> None:
        phase = self._phase
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._fail("网络错误：%s" % reply.errorString())
            reply.deleteLater()
            return
        try:
            if phase == "check":
                self._handle_check(reply)
            elif phase == "meta":
                self._handle_meta(reply)
            elif phase == "asset":
                self._handle_asset_done(reply)
        except Exception as e:
            log.exception("update flow error")
            self._fail("更新失败：%s" % e)
        finally:
            if phase != "asset":  # asset 落盘由 _handle_asset_done 收尾
                self._phase = "idle"
            reply.deleteLater()

    def _handle_check(self, reply: QNetworkReply) -> None:
        data = json.loads(bytes(reply.readAll()).decode("utf-8", "replace"))
        if data.get("draft") or data.get("prerelease"):
            self.checkFinished.emit(False, "", "")
            return
        tag = str(data.get("tag_name", "")).lstrip("vV")
        self._latest = tag
        from . import version
        if not is_newer(tag, version.VERSION):
            self.checkFinished.emit(False, tag, "")
            return
        notes = str(data.get("body") or "").strip()
        if len(notes) > 500:
            notes = notes[:500] + "..."
        self.checkFinished.emit(True, tag, notes)

    def _handle_meta(self, reply: QNetworkReply) -> None:
        data = json.loads(bytes(reply.readAll()).decode("utf-8", "replace"))
        asset = next((a for a in data.get("assets", [])
                      if ASSET_RE.search(str(a.get("name", "")))), None)
        if not asset:
            self._fail("Release 中未找到安装包资产")
            return
        url = str(asset.get("browser_download_url", ""))
        name = str(asset.get("name", "CountdownDesktop_Setup.exe"))
        self._file_path = os.path.join(tempfile.gettempdir(), name)
        self._phase = "asset"
        rep = self.nam.get(self._req(url))
        self._reply = rep
        rep.downloadProgress.connect(self._on_progress)
        rep.readyRead.connect(self._on_data)

    def _on_data(self) -> None:
        rep = self.sender()
        if self._fh is None:
            self._fh = open(self._file_path, "wb")
        self._fh.write(bytes(rep.readAll()))

    def _on_progress(self, received: int, total: int) -> None:
        if total > 0:
            self.downloadProgress.emit(int(received), int(total))

    def _handle_asset_done(self, reply: QNetworkReply) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        size = os.path.getsize(self._file_path) if os.path.exists(self._file_path) else 0
        if size < MIN_INSTALLER_BYTES:
            self._fail("下载文件过小（%d 字节），可能被网络策略拦截" % size)
            return
        self._phase = "idle"
        self.downloadFinished.emit(True, self._file_path)


def make_update_bat(installer_path: str,
                    exe_name: str = "CountdownDesktop.exe") -> str:
    """生成更新批处理：杀进程 → 静默安装（自动重启应用）→ 兜底拉起。"""
    bat = os.path.join(tempfile.gettempdir(), "CountdownDesktop_update.bat")
    content = """@echo off
rem Countdown Desktop auto-update
taskkill /F /IM {exe} /T >nul 2>&1
timeout /t 2 /nobreak >nul
"{installer}" /SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
timeout /t 3 /nobreak >nul
del "%~f0"
""".format(exe=exe_name, installer=installer_path)
    with open(bat, "w", encoding="ascii", errors="strict") as f:
        f.write(content)
    return bat


def run_update_bat(bat_path: str) -> None:
    """脱离主程序执行更新批处理（调用方随后退出主程序）。"""
    flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    subprocess.Popen(["cmd", "/c", bat_path], creationflags=flags, close_fds=True)
    log.info("update bat launched: %s", bat_path)
