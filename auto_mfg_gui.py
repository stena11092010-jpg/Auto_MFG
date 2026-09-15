#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto MultiFrame Generation — графический установщик мода генерации кадров.
Копирует version.dll + dlssg_sm86.ini рядом с игровым EXE
(Unreal Engine и другие движки).
"""

from __future__ import annotations

import shutil
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import tkinter as tk
from tkinter import ttk


APP_TITLE = "Auto MultiFrame Generation"
APP_VERSION = "1.2"

INI_NAME = "dlssg_sm86.ini"
SOURCE_DLL = "version.dll"
EXTRAS_MARKER = ".auto_mfg_extras.txt"
FORCE_MULT_CHOICES = ("2", "3", "4")
PROXY_CHOICES = (
    "version.dll",
    "winmm.dll",
    "dxgi.dll",
    "dbghelp.dll",
    "dinput8.dll",
    "winhttp.dll",
)

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


def resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def source_dll() -> Path:
    return resource_dir() / SOURCE_DLL


def source_ini() -> Path:
    return resource_dir() / INI_NAME


def missing_sources() -> list[str]:
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


def detect_engine(folder: Path, exe_name: str) -> str:
    lower = exe_name.lower()
    names = {p.name.lower() for p in folder.iterdir()} if folder.is_dir() else set()
    if lower.endswith("-win64-shipping.exe") or "unreal" in lower:
        return "Unreal"
    if "unityplayer.dll" in names or "gameassembly.dll" in names:
        return "Unity"
    if "sl.interposer.dll" in names or "nvngx_dlss.dll" in names or "nvngx_dlssg.dll" in names:
        return "DLSS-игра"
    if any(n.endswith(".pak") or n.endswith(".ucas") for n in names):
        return "Unreal"
    return "Другой"


def installed_status(folder: Path, proxy_name: str) -> bool:
    return (folder / proxy_name).is_file() and (folder / INI_NAME).is_file()


def backup_path(target: Path) -> Path:
    return target.with_name(target.name + ".mfgbak")


def extras_dir() -> Path:
    return resource_dir() / "extras"


def list_extra_files() -> list[Path]:
    folder = extras_dir()
    if not folder.is_dir():
        return []
    skip = {".txt", ".md"}
    files: list[Path] = []
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in skip and path.name.lower().startswith("readme"):
            continue
        files.append(path)
    return files


def build_force_ini(multiplier: int, base_text: str) -> str:
    """Пишет профиль принудительного запроса кадров.

    Native 0.2.4 читает MaxGeneratedFrames. Ключи ForceMultiplier / Enabled
    подхватывают более новые сборки того же проекта, лишние строки 0.2.4 игнорирует.
    """
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
    # Сохраняем исходные ключи, если пользователь правил базовый ini.
    if "HardwareBilinear=1" in base_text:
        lines = [ln.replace("HardwareBilinear=0", "HardwareBilinear=1") for ln in lines]
    if "Router=SM75" in base_text:
        lines = [ln.replace("Router=SM86", "Router=SM75") for ln in lines]
    return "\n".join(lines) + "\n"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE}  •  установщик  v{APP_VERSION}")
        self.geometry("960x740")
        self.minsize(800, 600)
        self.configure(bg="#12141a")

        self.scan_root = tk.StringVar(value="")
        self.scan_mode = tk.StringVar(value="any")
        self.proxy_name = tk.StringVar(value="version.dll")
        self.force_no_menu = tk.BooleanVar(value=False)
        self.force_mult = tk.StringVar(value="2")
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
            text="Установщик мода генерации кадров. Кладёт файлы рядом с игровым EXE — UE и другие движки.",
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

        opt_row = ttk.Frame(root)
        opt_row.pack(fill="x", padx=24, pady=(4, 4))
        ttk.Label(opt_row, text="Имя прокси-DLL:").pack(side="left")
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
            text="Если игра не подхватывает version.dll — смените имя.",
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

        ttk.Label(
            root,
            text="Без пункта в меню мод запросит кадры сам. Сработает, если игра уже умеет DLSS-G/Streamline. В игры без DLSS кадры этот пакет не добавит.",
            style="Muted.TLabel",
        ).pack(fill="x", padx=24, pady=(2, 0))

        ttk.Label(
            root,
            text="Можно указать папку игры, Steam\\steamapps\\common или сам EXE. Мод ставится в папку этого EXE.",
            style="Muted.TLabel",
        ).pack(fill="x", padx=24, pady=(2, 0))

        list_frame = ttk.Frame(root)
        list_frame.pack(fill="both", expand=True, padx=24, pady=(12, 8))

        columns = ("game", "engine", "folder", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("game", text="Исполняемый файл")
        self.tree.heading("engine", text="Движок")
        self.tree.heading("folder", text="Папка")
        self.tree.heading("status", text="Статус")
        self.tree.column("game", width=240, anchor="w")
        self.tree.column("engine", width=110, anchor="center")
        self.tree.column("folder", width=400, anchor="w")
        self.tree.column("status", width=130, anchor="center")

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

    def _check_sources(self) -> None:
        missing = missing_sources()
        if missing:
            self._log("Рядом со скриптом не найдены файлы: " + ", ".join(missing))
            self._log(f"Положите их в папку: {resource_dir()}")
            self.status_text.set("Нет файлов мода рядом со скриптом")
        else:
            self._log(f"Файлы мода найдены: {resource_dir()}")
            self._log(f"  • {SOURCE_DLL}  ({source_dll().stat().st_size} байт)")
            self._log(f"  • {INI_NAME}  ({source_ini().stat().st_size} байт)")
            self._log("Для игр не на UE выбирайте режим «Любые игры» или укажите EXE вручную.")
            extras = list_extra_files()
            if extras:
                self._log(f"Дополнительно из extras/: {len(extras)} файл(ов)")
            else:
                self._log("Папка extras/ пуста. Туда можно положить OptiScaler и подобные файлы — они скопируются вместе с модом.")

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
        return {
            "exe": exe.name,
            "folder": str(folder),
            "engine": detect_engine(folder, exe.name),
            "installed": installed_status(folder, proxy),
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
                found.append(
                    {
                        "exe": exe.name,
                        "folder": str(folder),
                        "engine": detect_engine(folder, exe.name),
                        "installed": installed_status(folder, proxy),
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

        # mode == "any": UE + Unity + DLSS-папки + крупные игровые EXE
        for exe in root.rglob(UE_GLOB):
            if exe.is_file() and not is_skipped_dir(exe.parent):
                results.append(exe)

        markers = {
            "unityplayer.dll",
            "gameassembly.dll",
            "nvngx_dlss.dll",
            "nvngx_dlssg.dll",
            "sl.interposer.dll",
            "sl.dlss_g.dll",
        }
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
            status = "установлен" if row["installed"] else "не установлен"
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(row["exe"], row["engine"], row["folder"], status),
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
        missing = missing_sources()
        if missing:
            messagebox.showerror(APP_TITLE, "Рядом со скриптом нет файлов мода:\n" + "\n".join(missing))
            return
        if not messagebox.askyesno(APP_TITLE, f"Установить мод прямо в папку?\n{folder}"):
            return
        row = {
            "exe": "(папка)",
            "folder": str(folder),
            "engine": detect_engine(folder, ""),
            "installed": installed_status(folder, self._current_proxy()),
        }
        self.found = [row]
        self._refresh_tree()
        self.tree.selection_set("0")
        self._apply(install=True)

    def _refresh_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        proxy = self._current_proxy()
        for i, row in enumerate(self.found):
            row["installed"] = installed_status(Path(row["folder"]), proxy)
            status = "установлен" if row["installed"] else "не установлен"
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(row["exe"], row.get("engine", "—"), row["folder"], status),
            )

    def _apply(self, install: bool) -> None:
        if self._busy:
            return
        idxs = self._selected_indices()
        if not idxs:
            messagebox.showwarning(APP_TITLE, "Выберите хотя бы одну игру в списке.")
            return
        if install:
            missing = missing_sources()
            if missing:
                messagebox.showerror(
                    APP_TITLE,
                    "Рядом со скриптом нет файлов мода:\n" + "\n".join(missing),
                )
                return
        action = "установить мод" if install else "удалить файлы мода"
        proxy = self._current_proxy()
        extra = f"\nПрокси: {proxy}" if install else ""
        force = bool(self.force_no_menu.get()) if install else False
        if install and force:
            extra += f"\nРежим: без пункта в меню, принудительно {self.force_mult.get()}×"
            extra += (
                "\n\nЭто не добавит генерацию в игру, которая вообще не умеет DLSS-G. "
                "Имеет смысл, если переключатель скрыт или серый."
            )
        if not messagebox.askyesno(APP_TITLE, f"{action.capitalize()} в {len(idxs)} папк(ах)?{extra}"):
            return
        self._set_busy(True)
        threading.Thread(
            target=self._apply_worker, args=(idxs, install, proxy, force), daemon=True
        ).start()

    def _apply_worker(
        self, idxs: list[int], install: bool, proxy: str, force: bool = False
    ) -> None:
        ok = 0
        fail = 0
        dll_src = source_dll()
        ini_src = source_ini()
        try:
            mult = int(self.force_mult.get() or "2")
        except ValueError:
            mult = 2
        for i in idxs:
            row = self.found[i]
            folder = Path(row["folder"])
            try:
                if install:
                    self._install_into(folder, proxy, dll_src, ini_src, force=force, multiplier=mult)
                    mode = f"force {mult}x" if force else "обычный"
                    self._log(f"Установлено ({proxy}, {mode}) → {folder}")
                    row["installed"] = True
                else:
                    self._uninstall_from(folder, proxy)
                    self._log(f"Удалено ← {folder}")
                    row["installed"] = False
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
        force: bool = False,
        multiplier: int = 2,
    ) -> None:
        folder.mkdir(parents=True, exist_ok=True)
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
            self._log(f"  ini: принудительный запрос {multiplier}×")
        else:
            shutil.copy2(ini_src, folder / INI_NAME)
        self._install_extras(folder)

    def _install_extras(self, folder: Path) -> None:
        extras = list_extra_files()
        if not extras:
            return
        root = extras_dir()
        copied: list[str] = []
        for src in extras:
            rel = src.relative_to(root)
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
            (folder / EXTRAS_MARKER).write_text("\n".join(copied) + "\n", encoding="utf-8")

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

    def _apply_done(self, ok: int, fail: int, install: bool) -> None:
        self._set_busy(False)
        verb = "Установка" if install else "Удаление"
        self.status_text.set(f"{verb}: успешно {ok}, ошибок {fail}")
        proxy = self._current_proxy()
        for i, row in enumerate(self.found):
            if self.tree.exists(str(i)):
                status = "установлен" if installed_status(Path(row["folder"]), proxy) else "не установлен"
                self.tree.item(
                    str(i),
                    values=(row["exe"], row.get("engine", "—"), row["folder"], status),
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
