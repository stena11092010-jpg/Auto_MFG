#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto MultiFrame Generation — графический установщик мода генерации кадров.
DLSS MFG (version.dll + dlssg_sm86.ini), FSR 3 FG и XeSS / XeFG.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import tkinter as tk
from tkinter import ttk


APP_TITLE = "Auto MultiFrame Generation"
APP_VERSION = "1.3"

INI_NAME = "dlssg_sm86.ini"
SOURCE_DLL = "version.dll"
OPTI_INI_NAME = "OptiScaler.ini"
UE_INI_NAME = "auto_mfg_Engine.ini"
EXTRAS_MARKER = ".auto_mfg_extras.txt"
UNLOCK_MARKER = ".auto_mfg_unlock.txt"
FORCE_MULT_CHOICES = ("2", "3", "4")
PROXY_CHOICES = (
    "version.dll",
    "winmm.dll",
    "dxgi.dll",
    "dbghelp.dll",
    "dinput8.dll",
    "winhttp.dll",
)
OPTI_PROXY_DEFAULT = "dxgi.dll"

UE_GLOB = "*-Win64-Shipping.exe"

SKIP_DIR_PARTS = {
    "easyanticheat",
    "eac",
    "battleye",
    "_commonredist",
    "redist",
    "directx",
    "vcredist",
    "dotnet",
    "crashpad",
    "crashreporter",
    "shadercache",
    "nvidia",
    "__overlay",
    "support",
    "redistributables",
    "prereqs",
    "thirdparty",
}

SKIP_EXE_PARTS = (
    "crash",
    "uninstall",
    "unins00",
    "setup",
    "redist",
    "vcredist",
    "dxsetup",
    "unitycrash",
    "easyanticheat",
    "beservice",
    "battleye",
    "cefsharp",
    "notification_helper",
    "qtwebengine",
    "werfault",
    "crashpad",
    "bootstrapper",
    "dotnet",
    "vc_redist",
    "installer",
    "repair",
    "overlay",
    "helper",
)

MIN_GENERIC_EXE_BYTES = 2 * 1024 * 1024

DLSS_MARKERS = {
    "nvngx_dlss.dll",
    "nvngx_dlssg.dll",
    "sl.interposer.dll",
    "sl.dlss_g.dll",
}
FSR_MARKERS = {
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_loader_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    "ffx_fsr3_x64.dll",
    "ffx_backend_dx12_x64.dll",
    "ffx_frameinterpolation_x64.dll",
    "ffx_fsr3upscaler_x64.dll",
    "dlssg_to_fsr3_amd_is_better.dll",
}
XESS_MARKERS = {
    "libxess.dll",
    "libxess_fg.dll",
    "libxell.dll",
    "libxess_dx11.dll",
    "sl.xess.dll",
}

FSR_NAME_HINTS = ("fsr", "fidelityfx", "ffx_fsr", "ffx_frame")
XESS_NAME_HINTS = ("xess", "xell", "xefg")


def resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def source_dll() -> Path:
    return resource_dir() / SOURCE_DLL


def source_ini() -> Path:
    return resource_dir() / INI_NAME


def profiles_dir() -> Path:
    return resource_dir() / "profiles"


def extras_dir() -> Path:
    return resource_dir() / "extras"


def missing_dlss_sources() -> list[str]:
    missing = []
    if not source_dll().is_file():
        missing.append(SOURCE_DLL)
    if not source_ini().is_file():
        missing.append(INI_NAME)
    return missing


def is_skipped_dir(path: Path) -> bool:
    return any(part.lower() in SKIP_DIR_PARTS for part in path.parts)


def is_junk_exe(path: Path) -> bool:
    name = path.name.lower()
    return any(part in name for part in SKIP_EXE_PARTS)


def _folder_names(folder: Path) -> set[str]:
    if not folder.is_dir():
        return set()
    try:
        return {p.name.lower() for p in folder.iterdir()}
    except OSError:
        return set()


def detect_fg_caps(folder: Path) -> list[str]:
    names = _folder_names(folder)
    caps: list[str] = []
    if names & DLSS_MARKERS or any(n.startswith("nvngx_dlss") or n.startswith("sl.dlss") for n in names):
        caps.append("DLSS")
    if names & FSR_MARKERS or any(any(h in n for h in FSR_NAME_HINTS) and n.endswith(".dll") for n in names):
        caps.append("FSR")
    if names & XESS_MARKERS or any(any(h in n for h in XESS_NAME_HINTS) and n.endswith(".dll") for n in names):
        caps.append("XeSS")
    return caps


def detect_engine(folder: Path, exe_name: str) -> str:
    lower = exe_name.lower()
    names = _folder_names(folder)
    if lower.endswith("-win64-shipping.exe") or "unreal" in lower:
        return "Unreal"
    if "unityplayer.dll" in names or "gameassembly.dll" in names:
        return "Unity"
    if names & DLSS_MARKERS:
        return "DLSS-игра"
    if any(n.endswith(".pak") or n.endswith(".ucas") for n in names):
        return "Unreal"
    return "Другой"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def install_label(folder: Path, proxy_name: str) -> str:
    tags: list[str] = []
    if (folder / proxy_name).is_file() and (folder / INI_NAME).is_file():
        tags.append("DLSS")
    opti = folder / OPTI_INI_NAME
    if opti.is_file():
        text = read_text(opti).lower()
        if "fgoutput=fsrfg" in text or "[fsrfg]" in text:
            if "FSR3" not in tags:
                tags.append("FSR3")
        if "fgoutput=xefg" in text or "unlockmfg=true" in text or "[xefg]" in text:
            if "XeSS" not in tags:
                tags.append("XeSS")
    ue = folder / UE_INI_NAME
    if ue.is_file():
        text = read_text(ue)
        if "FidelityFX.FI.Enabled" in text and "FSR3" not in tags:
            tags.append("FSR3")
        if ("XessFG" in text or "r.XeSS.Enabled" in text) and "XeSS" not in tags:
            tags.append("XeSS")
    if (folder / UNLOCK_MARKER).is_file():
        for line in read_text(folder / UNLOCK_MARKER).splitlines():
            key = line.strip().upper()
            if key in ("DLSS", "FSR3", "XESS") and key.replace("XESS", "XeSS") not in tags:
                tags.append("XeSS" if key == "XESS" else key)
    # unique preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return "+".join(ordered) if ordered else "не установлен"


def installed_status(folder: Path, proxy_name: str) -> bool:
    return install_label(folder, proxy_name) != "не установлен"


def backup_path(target: Path) -> Path:
    return target.with_name(target.name + ".mfgbak")


def list_extra_files(sub: str | None = None) -> list[Path]:
    folder = extras_dir() if not sub else extras_dir() / sub
    if not folder.is_dir():
        return []
    skip = {".txt", ".md"}
    files: list[Path] = []
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in skip and path.name.lower().startswith("readme"):
            continue
        # Nested extras (fsr3/xess/optiscaler) are handled by dedicated copy.
        if sub is None:
            try:
                rel = path.relative_to(extras_dir())
            except ValueError:
                continue
            if rel.parts and rel.parts[0].lower() in {"fsr3", "xess", "optiscaler"}:
                continue
        files.append(path)
    return files


def build_force_ini(multiplier: int, base_text: str) -> str:
    extra = max(1, min(3, multiplier - 1))
    lines = [
        "; Auto MultiFrame Generation — профиль «без переключателя в меню»",
        "; Перезапустите игру после изменения этого файла.",
        "[Compatibility]",
        "Router=SM86",
        "KernelImage=PTX",
        "HardwareBilinear=0",
        "",
        "[General]",
        "Enabled=1",
        "",
        "[FrameGeneration]",
        f"MaxGeneratedFrames={extra}",
        f"ForceMultiplier={multiplier}",
        "DynamicMFG=0",
        "",
        "[Logging]",
        "Level=1",
        "",
    ]
    if "HardwareBilinear=1" in base_text:
        lines = [ln.replace("HardwareBilinear=0", "HardwareBilinear=1") for ln in lines]
    if "Router=SM75" in base_text:
        lines = [ln.replace("Router=SM86", "Router=SM75") for ln in lines]
    return "\n".join(lines) + "\n"


def build_optiscaler_ini(
    *,
    fsr3: bool,
    xess: bool,
    output: str,
    multiplier: int,
) -> str:
    extra = max(1, min(5, multiplier - 1))
    fg_output = "xefg" if output == "xess" else "fsrfg"
    if xess and not fsr3:
        fg_output = "xefg"
    if fsr3 and not xess:
        fg_output = "fsrfg"
    if fg_output == "xefg":
        fg_input = "upscaler"
        ft_input = "2"
        dx12 = "xess"
        nvngx = "auto"
    else:
        fg_input = "fsrfg"
        ft_input = "0"
        dx12 = "ffx"
        nvngx = "Nukems"
    unlock = "true" if xess else "false"
    lines = [
        "; Auto MultiFrame Generation  v" + APP_VERSION,
        "; Сгенерированный OptiScaler.ini — FSR 3 / XeSS Frame Generation.",
        "; Insert — оверлей. Смена FG Input/Output → Save INI → полный перезапуск.",
        "",
        "[Upscalers]",
        "Dx11Upscaler=auto",
        f"Dx12Upscaler={dx12}",
        f"VulkanUpscaler={dx12}",
        "",
        "[FrameGen]",
        "Enabled=true",
        f"FGInput={fg_input}",
        f"FGOutput={fg_output}",
        f"FGNvngxReplacement={nvngx}",
        f"FTInput={ft_input}",
        "PreserveSwapChain=true",
        "SkipResizeBuffers=true",
        "",
        "[FSRFG]",
        "AllowAsync=true",
        "UseMutexForSwapchain=true",
        "FramePacingTuning=true",
        "FPTSafetyMarginInMs=0.01",
        "FPTVarianceFactor=0.3",
        "",
        "[XeFG]",
        "IgnoreInitChecks=false",
        f"InterpolationCount={extra}",
        f"UnlockMFG={unlock}",
        f"MaxInterpolatedFrames={extra}",
        "DepthInverted=true",
        "UIComposition=false",
        "",
    ]
    return "\n".join(lines)


def build_ue_engine_ini(*, fsr3: bool, xess: bool) -> str:
    lines = [
        "; Auto MultiFrame Generation — анлок нативных генераций Unreal Engine",
        "; Дубликат ключей, которые установщик также пытается вписать",
        "; в %LOCALAPPDATA%\\<Игра>\\Saved\\Config\\Windows\\Engine.ini",
        "",
    ]
    if fsr3:
        lines += [
            "[/Script/FFXFSR3Settings.FFXFSR3Settings]",
            "r.FidelityFX.FSR3.Enabled=True",
            "r.FidelityFX.FSR3.UseNativeDX12=True",
            "r.FidelityFX.FSR3.UseRHI=False",
            "r.FidelityFX.FI.Enabled=True",
            "r.FidelityFX.FI.OverrideSwapChainDX12=True",
            "",
        ]
    lines.append("[SystemSettings]")
    if fsr3:
        lines += [
            "r.FidelityFX.FSR3.Enabled=1",
            "r.FidelityFX.FSR3.UseNativeDX12=1",
            "r.FidelityFX.FSR3.UseRHI=0",
            "r.FidelityFX.FI.Enabled=1",
            "r.FidelityFX.FI.OverrideSwapChainDX12=1",
            "r.AntiAliasingMethod=0",
        ]
    if xess:
        lines += [
            "r.XeSS.Enabled=1",
            "r.XessFG.Enabled=1",
            "r.NGX.DLSS.DilateMotionVectors=0",
            "r.Streamline.DilateMotionVectors=0",
            "r.Streamline.InitializePlugin=1",
        ]
    lines.append("")
    return "\n".join(lines)


def _set_ini_key(section_body: str, key: str, value: str) -> str:
    prefix = key + "="
    lines = section_body.splitlines()
    out: list[str] = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(prefix.lower()):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and out[-1].strip() != "":
            out.append(f"{key}={value}")
        else:
            out.append(f"{key}={value}")
    return "\n".join(out)


def merge_ini_keys(text: str, section: str, keys: dict[str, str]) -> str:
    header = f"[{section}]"
    lower = text.replace("\r\n", "\n")
    if not lower.strip():
        body = "\n".join(f"{k}={v}" for k, v in keys.items())
        return f"{header}\n{body}\n"
    idx = -1
    lines = lower.split("\n")
    for i, line in enumerate(lines):
        if line.strip().lower() == header.lower():
            idx = i
            break
    if idx < 0:
        extra = header + "\n" + "\n".join(f"{k}={v}" for k, v in keys.items()) + "\n"
        if not lower.endswith("\n"):
            lower += "\n"
        return lower + "\n" + extra
    end = len(lines)
    for j in range(idx + 1, len(lines)):
        s = lines[j].strip()
        if s.startswith("[") and s.endswith("]"):
            end = j
            break
    body = "\n".join(lines[idx + 1 : end])
    for key, value in keys.items():
        body = _set_ini_key(body, key, value)
    new_lines = lines[: idx + 1] + body.split("\n") + lines[end:]
    result = "\n".join(new_lines)
    if not result.endswith("\n"):
        result += "\n"
    return result


def guess_ue_project_names(folder: Path, exe_name: str) -> list[str]:
    names: list[str] = []
    parts = list(folder.parts)
    for i, part in enumerate(parts):
        if part.lower() == "binaries" and i > 0:
            names.append(parts[i - 1])
    stem = Path(exe_name).stem
    if stem.lower().endswith("-win64-shipping"):
        names.append(stem[: -len("-win64-shipping")])
    elif stem:
        names.append(stem)
    names.append(folder.name)
    # unique, keep order, skip generic
    skip = {"win64", "binaries", "bin", "x64", "shipping", "game", "content"}
    out: list[str] = []
    seen: set[str] = set()
    for n in names:
        key = n.lower()
        if key in skip or key in seen or not n:
            continue
        seen.add(key)
        out.append(n)
    return out


def discover_ue_config_dirs(game_folder: Path, exe_name: str) -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path).lower()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    for parent in [game_folder, *game_folder.parents]:
        for sub in (
            Path("Saved") / "Config" / "Windows",
            Path("Saved") / "Config" / "WindowsNoEditor",
            Path("Saved") / "Config" / "WinGDK",
        ):
            p = parent / sub
            if p.is_dir():
                add(p)
        if parent.name.lower() in {
            "steamapps",
            "program files",
            "program files (x86)",
            "windows",
            "",
        }:
            break

    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        root = Path(local)
        for name in guess_ue_project_names(game_folder, exe_name):
            for sub in (
                Path("Saved") / "Config" / "Windows",
                Path("Saved") / "Config" / "WindowsNoEditor",
                Path("Saved") / "Config" / "WinGDK",
            ):
                p = root / name / sub
                if p.is_dir():
                    add(p)
                # also parent Saved path used by some titles
                p2 = root / name / "Saved" / "Config" / "Windows"
                if p2.is_dir():
                    add(p2)
    return found


def pick_opti_proxy(folder: Path, dlss_proxy: str) -> str:
    """OptiScaler must not share the DLSS MFG proxy name."""
    if dlss_proxy.lower() != OPTI_PROXY_DEFAULT.lower():
        return OPTI_PROXY_DEFAULT
    for name in PROXY_CHOICES:
        if name.lower() != dlss_proxy.lower():
            return name
    return "winmm.dll"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE}  •  установщик  v{APP_VERSION}")
        self.geometry("980x800")
        self.minsize(820, 640)
        self.configure(bg="#12141a")

        self.scan_root = tk.StringVar(value="")
        self.scan_mode = tk.StringVar(value="any")
        self.proxy_name = tk.StringVar(value="version.dll")
        self.force_no_menu = tk.BooleanVar(value=False)
        self.force_mult = tk.StringVar(value="2")
        self.unlock_dlss = tk.BooleanVar(value=True)
        self.unlock_fsr3 = tk.BooleanVar(value=True)
        self.unlock_xess = tk.BooleanVar(value=True)
        self.fg_output = tk.StringVar(value="fsr3")
        self.status_text = tk.StringVar(
            value="Выберите папку с игрой или библиотекой (Steam\\steamapps\\common)"
        )
        self.found: list[dict] = []
        self._busy = False

        self._setup_style()
        self._build_ui()
        self._check_sources()

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#12141a"
        card = "#1b1e27"
        fg = "#e8eaef"
        muted = "#9aa3b2"
        accent = "#5b8cff"
        accent_hover = "#7aa3ff"
        danger = "#e05b5b"

        style.configure(".", background=bg, foreground=fg, fieldbackground=card)
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=card)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=bg, foreground=fg, font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=bg, foreground=accent, font=("Segoe UI", 10))
        style.configure(
            "TEntry",
            fieldbackground=card,
            foreground=fg,
            insertcolor=fg,
            bordercolor="#2a2f3c",
            lightcolor="#2a2f3c",
            darkcolor="#2a2f3c",
        )
        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 8),
            borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", accent_hover), ("disabled", "#3a4254")])
        style.configure(
            "Ghost.TButton",
            background="#2a2f3c",
            foreground=fg,
            font=("Segoe UI", 10),
            padding=(12, 7),
            borderwidth=0,
        )
        style.map("Ghost.TButton", background=[("active", "#353b4b"), ("disabled", "#232733")])
        style.configure(
            "Danger.TButton",
            background="#3a2428",
            foreground=danger,
            font=("Segoe UI", 10),
            padding=(12, 7),
            borderwidth=0,
        )
        style.map("Danger.TButton", background=[("active", "#4a2c32")])
        style.configure(
            "Treeview",
            background=card,
            foreground=fg,
            fieldbackground=card,
            rowheight=28,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#232733",
            foreground=muted,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#2c3d66")], foreground=[("selected", "#ffffff")])
        style.configure("Horizontal.TProgressbar", troughcolor="#232733", background=accent, borderwidth=0)
        style.configure("TRadiobutton", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.map("TRadiobutton", background=[("active", bg)], foreground=[("selected", fg)])
        style.configure("TCombobox", fieldbackground=card, foreground=fg, background=card)
        style.configure("TCheckbutton", background=bg, foreground=fg, font=("Segoe UI", 10))

    def _build_ui(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", padx=24, pady=(20, 8))
        ttk.Label(header, text="Auto MultiFrame Generation", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Анлок генерации кадров: NVIDIA DLSS MFG, AMD FSR 3 и Intel XeSS (XeFG).",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        path_row = ttk.Frame(root)
        path_row.pack(fill="x", padx=24, pady=(16, 4))
        ttk.Label(path_row, text="Папка для поиска или установки").pack(anchor="w")

        entry_row = ttk.Frame(path_row)
        entry_row.pack(fill="x", pady=(6, 0))
        self.path_entry = ttk.Entry(entry_row, textvariable=self.scan_root)
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=6)
        ttk.Button(entry_row, text="Папка…", style="Ghost.TButton", command=self._browse).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(entry_row, text="Указать EXE…", style="Ghost.TButton", command=self._browse_exe).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(entry_row, text="Сканировать", style="Accent.TButton", command=self._start_scan).pack(
            side="left", padx=(8, 0)
        )

        mode_row = ttk.Frame(root)
        mode_row.pack(fill="x", padx=24, pady=(8, 4))
        ttk.Label(mode_row, text="Режим поиска:").pack(side="left")
        ttk.Radiobutton(
            mode_row, text="Любые игры", variable=self.scan_mode, value="any"
        ).pack(side="left", padx=(10, 0))
        ttk.Radiobutton(
            mode_row, text="Только Unreal (Win64-Shipping)", variable=self.scan_mode, value="ue"
        ).pack(side="left", padx=(10, 0))
        ttk.Radiobutton(
            mode_row, text="Все .exe", variable=self.scan_mode, value="all"
        ).pack(side="left", padx=(10, 0))

        unlock_row = ttk.Frame(root)
        unlock_row.pack(fill="x", padx=24, pady=(8, 2))
        ttk.Label(unlock_row, text="Анлок генераций:").pack(side="left")
        ttk.Checkbutton(
            unlock_row, text="DLSS MFG", variable=self.unlock_dlss, command=self._sync_unlock_ui
        ).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(
            unlock_row, text="FSR 3 FG", variable=self.unlock_fsr3, command=self._sync_unlock_ui
        ).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(
            unlock_row, text="XeSS FG (XeFG)", variable=self.unlock_xess, command=self._sync_unlock_ui
        ).pack(side="left", padx=(10, 0))
        ttk.Label(unlock_row, text="Основной выход FG:").pack(side="left", padx=(16, 0))
        self.output_combo = ttk.Combobox(
            unlock_row,
            textvariable=self.fg_output,
            values=("fsr3", "xess"),
            state="readonly",
            width=8,
        )
        self.output_combo.pack(side="left", padx=(8, 0))

        opt_row = ttk.Frame(root)
        opt_row.pack(fill="x", padx=24, pady=(4, 4))
        ttk.Label(opt_row, text="Имя прокси-DLL (DLSS):").pack(side="left")
        combo = ttk.Combobox(
            opt_row,
            textvariable=self.proxy_name,
            values=PROXY_CHOICES,
            state="readonly",
            width=16,
        )
        combo.pack(side="left", padx=(8, 0))
        ttk.Label(
            opt_row,
            text="OptiScaler (FSR/XeSS) ставится отдельно как dxgi.dll.",
            style="Muted.TLabel",
        ).pack(side="left", padx=(12, 0))

        force_row = ttk.Frame(root)
        force_row.pack(fill="x", padx=24, pady=(6, 2))
        ttk.Checkbutton(
            force_row,
            text="Игра без пункта генерации кадров",
            variable=self.force_no_menu,
            command=self._toggle_force,
        ).pack(side="left")
        ttk.Label(force_row, text="Принудительный множитель:").pack(side="left", padx=(16, 0))
        self.mult_combo = ttk.Combobox(
            force_row,
            textvariable=self.force_mult,
            values=FORCE_MULT_CHOICES,
            state="disabled",
            width=4,
        )
        self.mult_combo.pack(side="left", padx=(8, 0))
        ttk.Label(force_row, text="×", style="Muted.TLabel").pack(side="left", padx=(4, 0))

        self.hint_label = ttk.Label(
            root,
            text="",
            style="Muted.TLabel",
            wraplength=900,
        )
        self.hint_label.pack(fill="x", padx=24, pady=(2, 0))
        self._sync_unlock_ui()

        ttk.Label(
            root,
            text="Можно указать папку игры, Steam\\steamapps\\common или сам EXE. Мод ставится в папку этого EXE.",
            style="Muted.TLabel",
        ).pack(fill="x", padx=24, pady=(2, 0))

        list_frame = ttk.Frame(root)
        list_frame.pack(fill="both", expand=True, padx=24, pady=(12, 8))

        columns = ("game", "engine", "caps", "folder", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("game", text="Исполняемый файл")
        self.tree.heading("engine", text="Движок")
        self.tree.heading("caps", text="В игре")
        self.tree.heading("folder", text="Папка")
        self.tree.heading("status", text="Статус")
        self.tree.column("game", width=200, anchor="w")
        self.tree.column("engine", width=100, anchor="center")
        self.tree.column("caps", width=120, anchor="center")
        self.tree.column("folder", width=360, anchor="w")
        self.tree.column("status", width=140, anchor="center")

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btns = ttk.Frame(root)
        btns.pack(fill="x", padx=24, pady=(4, 8))
        ttk.Button(btns, text="Выбрать все", style="Ghost.TButton", command=self._select_all).pack(side="left")
        ttk.Button(btns, text="Снять выбор", style="Ghost.TButton", command=self._clear_sel).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(
            btns, text="В эту папку без поиска", style="Ghost.TButton", command=self._install_to_path
        ).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Удалить мод", style="Danger.TButton", command=self._uninstall).pack(side="right")
        ttk.Button(btns, text="Установить мод", style="Accent.TButton", command=self._install).pack(
            side="right", padx=(0, 8)
        )

        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(fill="x", padx=24, pady=(0, 6))

        ttk.Label(root, textvariable=self.status_text, style="Status.TLabel").pack(
            fill="x", padx=24, pady=(0, 6)
        )

        log_wrap = ttk.Frame(root)
        log_wrap.pack(fill="x", padx=24, pady=(0, 16))
        self.log = tk.Text(
            log_wrap,
            height=7,
            bg="#1b1e27",
            fg="#c5cbd6",
            insertbackground="#e8eaef",
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
        )
        self.log.pack(fill="x")
        self.log.configure(state="disabled")

    def _log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _selected_unlocks(self) -> dict[str, bool]:
        return {
            "dlss": bool(self.unlock_dlss.get()),
            "fsr3": bool(self.unlock_fsr3.get()),
            "xess": bool(self.unlock_xess.get()),
        }

    def _sync_unlock_ui(self) -> None:
        u = self._selected_unlocks()
        both_alt = u["fsr3"] and u["xess"]
        self.output_combo.configure(state="readonly" if both_alt else "disabled")
        parts: list[str] = []
        if u["dlss"]:
            parts.append("DLSS MFG — version.dll + dlssg_sm86.ini (нативный SM86).")
        if u["fsr3"]:
            parts.append(
                "FSR 3 — OptiScaler.ini (FGOutput=fsrfg) + анлок r.FidelityFX.FI в Engine.ini Unreal."
            )
        if u["xess"]:
            parts.append(
                "XeSS — OptiScaler.ini (XeFG, UnlockMFG) + DilateMotionVectors=0. Только borderless."
            )
        if not any(u.values()):
            parts.append("Включите хотя бы один анлок.")
        if u["fsr3"] or u["xess"]:
            parts.append(
                "DLL FidelityFX / XeSS / OptiScaler положите в extras\\fsr3, extras\\xess, extras\\optiscaler."
            )
        self.hint_label.configure(text=" ".join(parts))

    def _check_sources(self) -> None:
        missing = missing_dlss_sources()
        if missing:
            self._log("Рядом со скриптом не найдены файлы DLSS MFG: " + ", ".join(missing))
            self._log(f"Положите их в папку: {resource_dir()}")
            self._log("FSR 3 и XeSS можно ставить без этих файлов.")
        else:
            self._log(f"Файлы мода найдены: {resource_dir()}")
            self._log(f"  • {SOURCE_DLL}  ({source_dll().stat().st_size} байт)")
            self._log(f"  • {INI_NAME}  ({source_ini().stat().st_size} байт)")
        self._log("Анлок FSR 3 и XeSS FG включён. OptiScaler / FidelityFX / XeSS DLL — в extras\\.")
        extras = list_extra_files()
        extras += list_extra_files("fsr3")
        extras += list_extra_files("xess")
        extras += list_extra_files("optiscaler")
        if extras:
            self._log(f"Дополнительно из extras/: {len(extras)} файл(ов)")
        else:
            self._log(
                "Папка extras/ пуста. FSR 3 / XeSS всё равно получат ini-анлок; "
                "для OptiFG положите DLL в extras\\fsr3, extras\\xess или extras\\optiscaler."
            )

    def _toggle_force(self) -> None:
        self.mult_combo.configure(state="readonly" if self.force_no_menu.get() else "disabled")

    def _browse(self) -> None:
        folder = filedialog.askdirectory(title="Выберите папку с игрой или библиотекой")
        if folder:
            self.scan_root.set(folder)

    def _browse_exe(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите исполняемый файл игры",
            filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        exe = Path(path)
        self.scan_root.set(str(exe.parent))
        row = self._row_from_exe(exe)
        self._scan_done([row])
        self._log(f"Выбран EXE: {exe}")
        self.status_text.set(f"Готово к установке рядом с {exe.name}")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _current_proxy(self) -> str:
        name = self.proxy_name.get().strip() or SOURCE_DLL
        if name not in PROXY_CHOICES:
            return SOURCE_DLL
        return name

    def _row_from_exe(self, exe: Path) -> dict:
        folder = exe.parent
        proxy = self._current_proxy()
        caps = detect_fg_caps(folder)
        return {
            "exe": exe.name,
            "folder": str(folder),
            "engine": detect_engine(folder, exe.name),
            "caps": "+".join(caps) if caps else "—",
            "installed": installed_status(folder, proxy),
            "status": install_label(folder, proxy),
        }

    def _start_scan(self) -> None:
        if self._busy:
            return
        raw = self.scan_root.get().strip().strip('"')
        if not raw:
            messagebox.showwarning(APP_TITLE, "Сначала выберите папку для поиска.")
            return
        root = Path(raw)
        if root.is_file():
            root = root.parent
        if not root.is_dir():
            messagebox.showerror(APP_TITLE, f"Папка не найдена:\n{root}")
            return
        self._set_busy(True)
        mode = self.scan_mode.get()
        label = {"ue": "только Unreal", "any": "любые игры", "all": "все .exe"}.get(mode, mode)
        self.status_text.set(f"Идёт поиск ({label})…")
        self._log(f"Сканирование ({label}): {root}")
        threading.Thread(target=self._scan_worker, args=(root, mode), daemon=True).start()

    def _scan_worker(self, root: Path, mode: str) -> None:
        found: list[dict] = []
        seen: set[str] = set()
        try:
            candidates = self._collect_exes(root, mode)
            proxy = self._current_proxy()
            for exe in candidates:
                key = str(exe.resolve()).lower()
                if key in seen:
                    continue
                seen.add(key)
                folder = exe.parent
                caps = detect_fg_caps(folder)
                found.append(
                    {
                        "exe": exe.name,
                        "folder": str(folder),
                        "engine": detect_engine(folder, exe.name),
                        "caps": "+".join(caps) if caps else "—",
                        "installed": installed_status(folder, proxy),
                        "status": install_label(folder, proxy),
                    }
                )
            found.sort(key=lambda r: (r["engine"] != "Unreal", r["exe"].lower()))
        except Exception as exc:
            self.after(0, lambda: self._scan_done(found, error=str(exc)))
            return
        self.after(0, lambda: self._scan_done(found))

    def _collect_exes(self, root: Path, mode: str) -> list[Path]:
        results: list[Path] = []

        if mode == "ue":
            for exe in root.rglob(UE_GLOB):
                if exe.is_file() and not is_skipped_dir(exe.parent):
                    results.append(exe)
            return results

        if mode == "all":
            for exe in root.rglob("*.exe"):
                if exe.is_file() and not is_skipped_dir(exe.parent) and not is_junk_exe(exe):
                    results.append(exe)
            return results

        for exe in root.rglob(UE_GLOB):
            if exe.is_file() and not is_skipped_dir(exe.parent):
                results.append(exe)

        markers = set(DLSS_MARKERS) | set(FSR_MARKERS) | set(XESS_MARKERS)
        markers.update(
            {
                "unityplayer.dll",
                "gameassembly.dll",
            }
        )
        for marker_name in markers:
            for marker in root.rglob(marker_name):
                folder = marker.parent
                if is_skipped_dir(folder):
                    continue
                pick = self._pick_main_exe(folder)
                if pick:
                    results.append(pick)

        for exe in root.rglob("*.exe"):
            if not exe.is_file() or is_skipped_dir(exe.parent) or is_junk_exe(exe):
                continue
            try:
                size = exe.stat().st_size
            except OSError:
                continue
            if size >= MIN_GENERIC_EXE_BYTES:
                results.append(exe)

        return results

    def _pick_main_exe(self, folder: Path) -> Path | None:
        best: Path | None = None
        best_size = 0
        try:
            files = list(folder.glob("*.exe"))
        except OSError:
            return None
        for exe in files:
            if is_junk_exe(exe):
                continue
            name = exe.name.lower()
            if name.endswith("-win64-shipping.exe"):
                return exe
            try:
                size = exe.stat().st_size
            except OSError:
                continue
            if size > best_size:
                best = exe
                best_size = size
        return best

    def _scan_done(self, found: list[dict], error: str | None = None) -> None:
        self._set_busy(False)
        self.found = found
        for item in self.tree.get_children():
            self.tree.delete(item)
        if error:
            self.status_text.set("Ошибка поиска")
            self._log(f"Ошибка: {error}")
            return
        for i, row in enumerate(found):
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    row["exe"],
                    row["engine"],
                    row.get("caps", "—"),
                    row["folder"],
                    row.get("status", "не установлен"),
                ),
            )
        if found:
            self.status_text.set(f"Найдено целей: {len(found)}")
            self._log(f"Найдено совпадений: {len(found)}")
            self.tree.selection_set(self.tree.get_children())
        else:
            self.status_text.set("Ничего не найдено")
            self._log(
                "Ничего не найдено. Попробуйте режим «Все .exe» или кнопку «Указать EXE…» / «В эту папку без поиска»."
            )

    def _selected_indices(self) -> list[int]:
        return [int(i) for i in self.tree.selection()]

    def _select_all(self) -> None:
        self.tree.selection_set(self.tree.get_children())

    def _clear_sel(self) -> None:
        self.tree.selection_remove(self.tree.get_children())

    def _install(self) -> None:
        self._apply(install=True)

    def _uninstall(self) -> None:
        self._apply(install=False)

    def _install_to_path(self) -> None:
        if self._busy:
            return
        raw = self.scan_root.get().strip().strip('"')
        if not raw:
            messagebox.showwarning(APP_TITLE, "Укажите папку, куда ставить мод.")
            return
        folder = Path(raw)
        if folder.is_file():
            folder = folder.parent
        if not folder.is_dir():
            messagebox.showerror(APP_TITLE, f"Папка не найдена:\n{folder}")
            return
        if not any(self._selected_unlocks().values()):
            messagebox.showwarning(APP_TITLE, "Включите хотя бы один анлок: DLSS, FSR 3 или XeSS.")
            return
        u = self._selected_unlocks()
        if u["dlss"]:
            missing = missing_dlss_sources()
            if missing:
                messagebox.showerror(APP_TITLE, "Рядом со скриптом нет файлов DLSS MFG:\n" + "\n".join(missing))
                return
        if not messagebox.askyesno(APP_TITLE, f"Установить мод прямо в папку?\n{folder}"):
            return
        row = self._row_from_exe(folder / "(папка)")
        row["exe"] = "(папка)"
        row["engine"] = detect_engine(folder, "")
        row["caps"] = "+".join(detect_fg_caps(folder)) or "—"
        self.found = [row]
        self._refresh_tree()
        self.tree.selection_set("0")
        self._apply(install=True)

    def _refresh_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        proxy = self._current_proxy()
        for i, row in enumerate(self.found):
            folder = Path(row["folder"])
            row["installed"] = installed_status(folder, proxy)
            row["status"] = install_label(folder, proxy)
            row["caps"] = row.get("caps") or "+".join(detect_fg_caps(folder)) or "—"
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    row["exe"],
                    row.get("engine", "—"),
                    row.get("caps", "—"),
                    row["folder"],
                    row["status"],
                ),
            )

    def _apply(self, install: bool) -> None:
        if self._busy:
            return
        idxs = self._selected_indices()
        if not idxs:
            messagebox.showwarning(APP_TITLE, "Выберите хотя бы одну игру в списке.")
            return
        u = self._selected_unlocks()
        if install:
            if not any(u.values()):
                messagebox.showwarning(APP_TITLE, "Включите хотя бы один анлок: DLSS, FSR 3 или XeSS.")
                return
            if u["dlss"]:
                missing = missing_dlss_sources()
                if missing:
                    messagebox.showerror(
                        APP_TITLE,
                        "Рядом со скриптом нет файлов DLSS MFG:\n" + "\n".join(missing),
                    )
                    return
        action = "установить мод" if install else "удалить файлы мода"
        proxy = self._current_proxy()
        extra = ""
        if install:
            chosen = [n for n, on in (("DLSS MFG", u["dlss"]), ("FSR 3", u["fsr3"]), ("XeSS", u["xess"])) if on]
            extra += "\nАнлок: " + ", ".join(chosen)
            extra += f"\nПрокси DLSS: {proxy}"
            if u["fsr3"] or u["xess"]:
                extra += f"\nПрокси OptiScaler: {pick_opti_proxy(Path('.'), proxy)}"
                extra += f"\nОсновной выход FG: {'XeSS / XeFG' if self.fg_output.get() == 'xess' else 'FSR 3'}"
        force = bool(self.force_no_menu.get()) if install else False
        if install and force:
            extra += f"\nРежим: без пункта в меню, принудительно {self.force_mult.get()}×"
            extra += (
                "\n\nПринудительный множитель относится к DLSS MFG. "
                "FSR 3 / XeSS пишут тот же множитель в OptiScaler.ini (InterpolationCount)."
            )
        if not messagebox.askyesno(APP_TITLE, f"{action.capitalize()} в {len(idxs)} папк(ах)?{extra}"):
            return
        self._set_busy(True)
        threading.Thread(
            target=self._apply_worker, args=(idxs, install, proxy, force, dict(u)), daemon=True
        ).start()

    def _apply_worker(
        self,
        idxs: list[int],
        install: bool,
        proxy: str,
        force: bool,
        unlocks: dict[str, bool],
    ) -> None:
        ok = 0
        fail = 0
        dll_src = source_dll()
        ini_src = source_ini()
        try:
            mult = int(self.force_mult.get() or "2")
        except ValueError:
            mult = 2
        output = self.fg_output.get() or "fsr3"
        for i in idxs:
            row = self.found[i]
            folder = Path(row["folder"])
            try:
                if install:
                    self._install_into(
                        folder,
                        proxy,
                        dll_src,
                        ini_src,
                        force=force,
                        multiplier=mult,
                        unlocks=unlocks,
                        output=output,
                        exe_name=str(row.get("exe") or ""),
                    )
                    flags = "+".join(
                        n for n, on in (("DLSS", unlocks["dlss"]), ("FSR3", unlocks["fsr3"]), ("XeSS", unlocks["xess"])) if on
                    )
                    self._log(f"Установлено ({flags}) → {folder}")
                    row["installed"] = True
                    row["status"] = install_label(folder, proxy)
                else:
                    self._uninstall_from(folder, proxy)
                    self._log(f"Удалено ← {folder}")
                    row["installed"] = False
                    row["status"] = "не установлен"
                ok += 1
            except Exception as exc:
                fail += 1
                self._log(f"Ошибка в {folder}: {exc}")
        self.after(0, lambda: self._apply_done(ok, fail, install))

    def _install_into(
        self,
        folder: Path,
        proxy: str,
        dll_src: Path,
        ini_src: Path,
        force: bool,
        multiplier: int,
        unlocks: dict[str, bool],
        output: str,
        exe_name: str,
    ) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        if unlocks.get("dlss"):
            self._install_dlss(folder, proxy, dll_src, ini_src, force, multiplier)
            written.append("DLSS")
        if unlocks.get("fsr3") or unlocks.get("xess"):
            self._install_alt_fg(folder, proxy, unlocks, output, multiplier, exe_name)
            if unlocks.get("fsr3"):
                written.append("FSR3")
            if unlocks.get("xess"):
                written.append("XeSS")
        self._install_extras(folder, extras_dir(), list_extra_files(), written)
        (folder / UNLOCK_MARKER).write_text("\n".join(written) + "\n", encoding="utf-8")

    def _install_dlss(
        self,
        folder: Path,
        proxy: str,
        dll_src: Path,
        ini_src: Path,
        force: bool,
        multiplier: int,
    ) -> None:
        target_dll = folder / proxy
        if target_dll.is_file():
            bak = backup_path(target_dll)
            same = False
            try:
                same = target_dll.stat().st_size == dll_src.stat().st_size
            except OSError:
                same = False
            if not same and not bak.is_file():
                shutil.copy2(target_dll, bak)
                self._log(f"  резервная копия: {bak.name}")
        shutil.copy2(dll_src, target_dll)
        if force:
            base_text = ini_src.read_text(encoding="utf-8", errors="ignore") if ini_src.is_file() else ""
            (folder / INI_NAME).write_text(build_force_ini(multiplier, base_text), encoding="utf-8")
            self._log(f"  ini DLSS: принудительный запрос {multiplier}×")
        else:
            shutil.copy2(ini_src, folder / INI_NAME)
        self._log(f"  DLSS MFG: {proxy} + {INI_NAME}")

    def _install_alt_fg(
        self,
        folder: Path,
        dlss_proxy: str,
        unlocks: dict[str, bool],
        output: str,
        multiplier: int,
        exe_name: str,
    ) -> None:
        fsr3 = bool(unlocks.get("fsr3"))
        xess = bool(unlocks.get("xess"))
        opti_text = build_optiscaler_ini(fsr3=fsr3, xess=xess, output=output, multiplier=multiplier)
        opti_path = folder / OPTI_INI_NAME
        if opti_path.is_file() and not backup_path(opti_path).is_file():
            shutil.copy2(opti_path, backup_path(opti_path))
        opti_path.write_text(opti_text, encoding="utf-8")
        self._log(f"  {OPTI_INI_NAME}: FGOutput={'xefg' if (xess and (not fsr3 or output == 'xess')) else 'fsrfg'}")

        ue_text = build_ue_engine_ini(fsr3=fsr3, xess=xess)
        (folder / UE_INI_NAME).write_text(ue_text, encoding="utf-8")
        self._log(f"  {UE_INI_NAME}: нативный анлок Unreal")

        patched = self._patch_ue_engine_inis(folder, exe_name, fsr3=fsr3, xess=xess)
        if patched:
            self._log(f"  Engine.ini обновлён: {patched}")
        else:
            self._log(
                "  Engine.ini в %LOCALAPPDATA% не найден — ключи лежат в auto_mfg_Engine.ini, "
                "вставьте их вручную при необходимости."
            )

        self._install_extras(folder, extras_dir() / "fsr3", list_extra_files("fsr3"), [])
        self._install_extras(folder, extras_dir() / "xess", list_extra_files("xess"), [])
        self._install_optiscaler_proxy(folder, dlss_proxy)

    def _install_optiscaler_proxy(self, folder: Path, dlss_proxy: str) -> None:
        opti_files = list_extra_files("optiscaler")
        if not opti_files:
            return
        proxy_name = pick_opti_proxy(folder, dlss_proxy)
        root = extras_dir() / "optiscaler"
        for src in opti_files:
            name = src.name
            if name.lower() in {"optiscaler.dll", "nvngx.dll"}:
                dest = folder / proxy_name
            else:
                dest = folder / src.relative_to(root)
                dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and dest.suffix.lower() == ".dll" and not backup_path(dest).is_file():
                shutil.copy2(dest, backup_path(dest))
            shutil.copy2(src, dest)
            self._log(f"  optiscaler: {src.name} → {dest.name}")

    def _patch_ue_engine_inis(
        self, folder: Path, exe_name: str, *, fsr3: bool, xess: bool
    ) -> int:
        keys_sys: dict[str, str] = {}
        if fsr3:
            keys_sys.update(
                {
                    "r.FidelityFX.FSR3.Enabled": "1",
                    "r.FidelityFX.FSR3.UseNativeDX12": "1",
                    "r.FidelityFX.FSR3.UseRHI": "0",
                    "r.FidelityFX.FI.Enabled": "1",
                    "r.FidelityFX.FI.OverrideSwapChainDX12": "1",
                }
            )
        if xess:
            keys_sys.update(
                {
                    "r.XeSS.Enabled": "1",
                    "r.XessFG.Enabled": "1",
                    "r.NGX.DLSS.DilateMotionVectors": "0",
                    "r.Streamline.DilateMotionVectors": "0",
                }
            )
        ffx_keys = {
            "r.FidelityFX.FSR3.Enabled": "True",
            "r.FidelityFX.FSR3.UseNativeDX12": "True",
            "r.FidelityFX.FSR3.UseRHI": "False",
            "r.FidelityFX.FI.Enabled": "True",
            "r.FidelityFX.FI.OverrideSwapChainDX12": "True",
        }
        count = 0
        for cfg_dir in discover_ue_config_dirs(folder, exe_name):
            engine = cfg_dir / "Engine.ini"
            try:
                cfg_dir.mkdir(parents=True, exist_ok=True)
                original = read_text(engine) if engine.is_file() else ""
                if engine.is_file() and not backup_path(engine).is_file():
                    shutil.copy2(engine, backup_path(engine))
                text = original
                if fsr3:
                    text = merge_ini_keys(text, "/Script/FFXFSR3Settings.FFXFSR3Settings", ffx_keys)
                text = merge_ini_keys(text, "SystemSettings", keys_sys)
                engine.write_text(text, encoding="utf-8")
                count += 1
                self._log(f"  Engine.ini: {engine}")
            except OSError as exc:
                self._log(f"  не удалось записать {engine}: {exc}")
        return count

    def _install_extras(
        self, folder: Path, root: Path, extras: list[Path], _written: list[str]
    ) -> None:
        if not extras:
            return
        copied: list[str] = []
        marker = folder / EXTRAS_MARKER
        existing = [ln.strip() for ln in read_text(marker).splitlines() if ln.strip()] if marker.is_file() else []
        for src in extras:
            try:
                rel = src.relative_to(root)
            except ValueError:
                rel = Path(src.name)
            dest = folder / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and dest.suffix.lower() == ".dll":
                bak = backup_path(dest)
                if not bak.is_file():
                    shutil.copy2(dest, bak)
            shutil.copy2(src, dest)
            copied.append(str(rel).replace("\\", "/"))
            self._log(f"  extras: {rel}")
        if copied:
            merged = existing + [c for c in copied if c not in existing]
            marker.write_text("\n".join(merged) + "\n", encoding="utf-8")

    def _uninstall_from(self, folder: Path, proxy: str) -> None:
        target_dll = folder / proxy
        bak = backup_path(target_dll)
        ini = folder / INI_NAME
        if target_dll.is_file():
            target_dll.unlink()
        if bak.is_file():
            shutil.copy2(bak, target_dll)
            bak.unlink()
            self._log(f"  восстановлен оригинал: {proxy}")
        if ini.is_file():
            ini.unlink()
        for name in (OPTI_INI_NAME, UE_INI_NAME):
            path = folder / name
            pbak = backup_path(path)
            if path.is_file():
                path.unlink()
            if pbak.is_file():
                shutil.copy2(pbak, path)
                pbak.unlink()
                self._log(f"  восстановлен: {name}")
        for cfg_dir in discover_ue_config_dirs(folder, ""):
            engine = cfg_dir / "Engine.ini"
            ebak = backup_path(engine)
            if ebak.is_file():
                shutil.copy2(ebak, engine)
                ebak.unlink()
                self._log(f"  восстановлен Engine.ini: {engine}")
        marker = folder / EXTRAS_MARKER
        if marker.is_file():
            for line in marker.read_text(encoding="utf-8", errors="ignore").splitlines():
                rel = line.strip()
                if not rel:
                    continue
                extra = folder / rel
                extra_bak = backup_path(extra)
                if extra.is_file():
                    extra.unlink()
                if extra_bak.is_file():
                    shutil.copy2(extra_bak, extra)
                    extra_bak.unlink()
                    self._log(f"  восстановлен extras: {rel}")
            marker.unlink()
        # OptiScaler proxy leftover (dxgi etc.)
        for name in PROXY_CHOICES:
            if name.lower() == proxy.lower():
                continue
            leftover = folder / name
            lbak = backup_path(leftover)
            if leftover.is_file() and lbak.is_file():
                leftover.unlink()
                shutil.copy2(lbak, leftover)
                lbak.unlink()
                self._log(f"  восстановлен прокси: {name}")
        um = folder / UNLOCK_MARKER
        if um.is_file():
            um.unlink()

    def _apply_done(self, ok: int, fail: int, install: bool) -> None:
        self._set_busy(False)
        verb = "Установка" if install else "Удаление"
        self.status_text.set(f"{verb}: успешно {ok}, ошибок {fail}")
        proxy = self._current_proxy()
        for i, row in enumerate(self.found):
            if self.tree.exists(str(i)):
                status = install_label(Path(row["folder"]), proxy)
                self.tree.item(
                    str(i),
                    values=(
                        row["exe"],
                        row.get("engine", "—"),
                        row.get("caps", "—"),
                        row["folder"],
                        status,
                    ),
                )
        if fail:
            messagebox.showwarning(APP_TITLE, f"{verb} завершена с ошибками.\nУспешно: {ok}\nОшибок: {fail}")
        elif ok:
            messagebox.showinfo(APP_TITLE, f"{verb} завершена.\nОбработано папок: {ok}")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
