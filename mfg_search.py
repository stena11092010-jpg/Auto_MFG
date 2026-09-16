#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto MultiFrame Generation — модуль поиска.

Перенос логики веб-сканера в десктопное приложение:
  • каталог известных игр (DLSS-G / скрытый пункт / нет DLSS-G / онлайн);
  • ключевые слова и русские алиасы (энджин, бинари, шиппинг, юнити, длсс…);
  • сигнатуры путей (Engine/Binaries/Win64, UnityPlayer, bin/x64 и т.д.);
  • автоматический подбор библиотек Steam / Epic / Xbox / GOG на всех дисках.

Модуль не зависит от tkinter — его можно использовать отдельно.
"""

from __future__ import annotations

import os
import re
import string
from pathlib import Path


# --------------------------------------------------------------------------
# Каталог известных игр
# --------------------------------------------------------------------------
# (exe, название, движок, dlssg, онлайн, примечание)
#   dlssg: native   — генерация кадров есть в меню
#          hidden   — пункт есть, но скрыт/серый → помогает принудительный режим
#          none     — своей DLSS-G нет, пакет кадры не добавит
_CATALOG_ROWS = [
    ("b1-Win64-Shipping.exe", "Black Myth: Wukong", "Unreal", "native", False, None),
    ("HogwartsLegacy.exe", "Hogwarts Legacy", "Unreal", "native", False, None),
    ("Stalker2-Win64-Shipping.exe", "S.T.A.L.K.E.R. 2: Heart of Chornobyl", "Unreal", "native", False, None),
    ("Sandfall-Win64-Shipping.exe", "Clair Obscur: Expedition 33", "Unreal", "native", False, None),
    ("SHProto-Win64-Shipping.exe", "Silent Hill 2", "Unreal", "native", False, None),
    ("Hellblade2-Win64-Shipping.exe", "Senua's Saga: Hellblade II", "Unreal", "native", False, None),
    ("Remnant2-Win64-Shipping.exe", "Remnant II", "Unreal", "native", False, None),
    ("LiesofP-Win64-Shipping.exe", "Lies of P", "Unreal", "native", False, None),
    ("Palworld-Win64-Shipping.exe", "Palworld", "Unreal", "hidden", False,
     "Пункт генерации кадров может быть скрыт — включите принудительный множитель."),
    ("FactoryGameSteam-Win64-Shipping.exe", "Satisfactory", "Unreal", "native", False, None),
    ("RoboCop-Win64-Shipping.exe", "RoboCop: Rogue City", "Unreal", "native", False, None),
    ("AtomicHeart-Win64-Shipping.exe", "Atomic Heart", "Unreal", "native", False, None),
    ("JediSurvivor.exe", "Star Wars Jedi: Survivor", "Unreal", "native", False, None),
    ("KingdomCome.exe", "Kingdom Come: Deliverance II", "Unreal", "native", False, None),
    ("Darktide-Win64-Shipping.exe", "Warhammer 40,000: Darktide", "Unreal", "native", True, None),
    ("Talos2-Win64-Shipping.exe", "The Talos Principle 2", "Unreal", "native", False, None),
    ("LOTF2-Win64-Shipping.exe", "Lords of the Fallen", "Unreal", "native", False, None),
    ("SparkingZERO-Win64-Shipping.exe", "DRAGON BALL: Sparking! ZERO", "Unreal", "native", False, None),
    ("ArkAscended.exe", "ARK: Survival Ascended", "Unreal", "native", True, None),
    ("Client-Win64-Shipping.exe", "Wuthering Waves", "Unreal", "hidden", True, None),
    ("M1-Win64-Shipping.exe", "The First Descendant", "Unreal", "native", True, None),
    ("Marvel-Win64-Shipping.exe", "Marvel Rivals", "Unreal", "native", True, None),
    ("FortniteClient-Win64-Shipping.exe", "Fortnite", "Unreal", "native", True,
     "Онлайн с античитом — сторонний прокси ставить нельзя."),
    ("Polaris-Win64-Shipping.exe", "TEKKEN 8", "Unreal", "native", True, None),
    ("StillWakesTheDeep-Win64-Shipping.exe", "Still Wakes the Deep", "Unreal", "native", False, None),
    ("Oregon-Win64-Shipping.exe", "High On Life", "Unreal", "hidden", False, None),
    ("Cyberpunk2077.exe", "Cyberpunk 2077", "REDengine", "native", False, None),
    ("witcher3.exe", "The Witcher 3: Wild Hunt", "REDengine", "native", False,
     "Ставьте мод в bin\\x64_dx12, не в x64."),
    ("MonsterHunterWilds.exe", "Monster Hunter Wilds", "RE Engine", "native", False, None),
    ("DD2.exe", "Dragon's Dogma 2", "RE Engine", "native", False, None),
    ("re4.exe", "Resident Evil 4", "RE Engine", "native", False, None),
    ("StreetFighter6.exe", "Street Fighter 6", "RE Engine", "native", True, None),
    ("AlanWake2.exe", "Alan Wake 2", "Northlight", "native", False, None),
    ("Control_DX12.exe", "Control", "Northlight", "hidden", False, None),
    ("HorizonForbiddenWest.exe", "Horizon Forbidden West", "Decima", "native", False, None),
    ("ds.exe", "Death Stranding Director's Cut", "Decima", "native", False, None),
    ("Spider-Man2.exe", "Marvel's Spider-Man 2", "Insomniac", "native", False, None),
    ("GhostOfTsushima.exe", "Ghost of Tsushima", "Insomniac", "native", False, None),
    ("GoWR.exe", "God of War Ragnarök", "Другой", "native", False, None),
    ("TheGreatCircle.exe", "Indiana Jones and the Great Circle", "id Tech", "native", False, None),
    ("DOOMTheDarkAges.exe", "DOOM: The Dark Ages", "id Tech", "native", False, None),
    ("Outlaws.exe", "Star Wars Outlaws", "Snowdrop", "native", False, None),
    ("afop.exe", "Avatar: Frontiers of Pandora", "Snowdrop", "native", False, None),
    ("ACShadows.exe", "Assassin's Creed Shadows", "Dunia", "native", False, None),
    ("Diablo IV.exe", "Diablo IV", "Другой", "native", True, None),
    ("eldenring.exe", "ELDEN RING", "FromSoftware", "none", True,
     "Своей DLSS-G нет — пакет кадры не добавит."),
    ("nightreign.exe", "ELDEN RING NIGHTREIGN", "FromSoftware", "none", True, None),
    ("smb2-win64-shipping.exe", "Warhammer 40,000: Space Marine 2", "Saber", "native", False, None),
    ("helldivers2.exe", "HELLDIVERS 2", "Другой", "native", True, None),
    ("GenshinImpact.exe", "Genshin Impact", "Unity", "none", True, None),
    ("ZenlessZoneZero.exe", "Zenless Zone Zero", "Unity", "hidden", True, None),
    ("Lethal Company.exe", "Lethal Company", "Unity", "none", True, None),
    ("Hollow Knight Silksong.exe", "Hollow Knight: Silksong", "Unity", "none", False, None),
    ("Cities2.exe", "Cities: Skylines II", "Unity", "hidden", False, None),
    ("bg3.exe", "Baldur's Gate 3", "Другой", "none", False,
     "Divinity engine. Мод имеет смысл только если уже есть Streamline/DLSS-G."),
]

CATALOG: dict[str, dict] = {}
for _exe, _name, _engine, _dlssg, _online, _notes in _CATALOG_ROWS:
    CATALOG[_exe.lower()] = {
        "exe": _exe,
        "name": _name,
        "engine": _engine,
        "dlssg": _dlssg,
        "online": _online,
        "notes": _notes,
    }

DLSSG_LABEL = {
    "native": "DLSS-G есть",
    "hidden": "пункт скрыт",
    "streamline": "Streamline",
    "none": "нет DLSS-G",
    "unknown": "—",
}


def catalog_lookup(exe_name: str, folder: str | Path = "") -> dict | None:
    """Ищет игру в каталоге по имени EXE, затем по названию папки."""
    hit = CATALOG.get(exe_name.lower())
    if hit:
        return hit
    folder_low = str(folder).lower()
    if not folder_low:
        return None
    for entry in CATALOG.values():
        simple = re.sub(r"[^a-z0-9]+", "", entry["name"].lower())
        if len(simple) < 5:
            continue
        if simple in re.sub(r"[^a-z0-9]+", "", folder_low):
            return entry
    return None


# --------------------------------------------------------------------------
# Ключевые слова и алиасы
# --------------------------------------------------------------------------
# (id, подпись на кнопке, подсказка, токены)
KEYWORDS: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("engine", "Engine", "папка Engine / слово engine в пути", ("engine",)),
    ("binaries", "Binaries", "Binaries, binary, bin/x64", ("binaries", "binary")),
    ("win64", "Win64", "Win64 / x64 исполняемые", ("win64", "x64")),
    ("shipping", "Shipping", "*-Win64-Shipping.exe", ("shipping", "win64-shipping")),
    ("unreal", "Unreal", "Unreal Engine, .pak / .ucas", ("unreal", "shipping")),
    ("unity", "Unity", "UnityPlayer.dll", ("unity", "unityplayer")),
    ("gameassembly", "GameAssembly", "IL2CPP runtime", ("gameassembly", "il2cpp")),
    ("dlss", "DLSS", "nvngx_dlss / dlssg", ("dlss", "nvngx", "dlssg")),
    ("streamline", "Streamline", "sl.interposer.dll", ("streamline", "interposer", "sl.dlss")),
    ("redengine", "REDengine", "CDPR bin/x64", ("redengine", "cyberpunk", "witcher")),
    ("reengine", "RE Engine", "Capcom RE Engine", ("reengine", "re engine", "capcom")),
]

KEYWORD_TOKENS = {kw[0]: kw[3] for kw in KEYWORDS}

ALIAS_EXPAND: dict[str, tuple[str, ...]] = {
    "энджин": ("engine",),
    "енджин": ("engine",),
    "движок": ("engine", "unreal", "unity"),
    "бинари": ("binaries", "binary"),
    "бинар": ("binaries", "binary"),
    "бинарник": ("binaries", "binary", "exe"),
    "шиппинг": ("shipping", "win64-shipping"),
    "вин64": ("win64",),
    "юнити": ("unity", "unityplayer"),
    "анрил": ("unreal", "win64-shipping"),
    "анреал": ("unreal",),
    "длсс": ("dlss", "nvngx_dlss"),
    "длс": ("dlss",),
    "мфг": ("dlss", "dlssg", "mfg"),
    "экзе": ("exe",),
    "ехе": ("exe",),
    "стримлайн": ("streamline", "interposer"),
    "онлайн": ("online",),
    "сетевая": ("online",),
    "игра": (),
    "engine": ("engine",),
    "engines": ("engine",),
    "binary": ("binaries", "binary"),
    "binaries": ("binaries", "binary"),
    "bin": ("binaries", "bin", "x64"),
    "win64": ("win64",),
    "shipping": ("shipping", "win64-shipping"),
    "unity": ("unity", "unityplayer"),
    "unityplayer": ("unity", "unityplayer"),
    "unreal": ("unreal", "engine", "binaries", "shipping"),
    "ue": ("unreal",),
    "dlss": ("dlss", "nvngx"),
    "mfg": ("dlss", "dlssg"),
    "streamline": ("streamline", "interposer"),
}

SIGNATURES = [
    ("Unreal · Engine / Binaries / Win64", "Game\\Binaries\\Win64\\*-Win64-Shipping.exe"),
    ("Unity · UnityPlayer", "Game\\UnityPlayer.dll + Game.exe"),
    ("Unity IL2CPP · GameAssembly", "Game\\GameAssembly.dll"),
    ("REDengine · bin/x64", "bin\\x64\\Cyberpunk2077.exe"),
    ("NVIDIA DLSS / DLSS-G", "nvngx_dlss.dll · nvngx_dlssg.dll"),
    ("NVIDIA Streamline", "sl.interposer.dll · sl.dlss_g.dll"),
]

_PUNCT_RE = re.compile(r"[^\w.]+", re.UNICODE)


def normalize_token(raw: str) -> str:
    return _PUNCT_RE.sub(" ", raw.lower().replace("ё", "е")).strip()


def tokenize_query(query: str) -> list[str]:
    return [t for t in normalize_token(query).split() if len(t) >= 2]


def expand_tokens(tokens: list[str]) -> list[str]:
    out: set[str] = set()
    for token in tokens:
        out.add(token)
        for item in ALIAS_EXPAND.get(token, ()):
            out.add(item)
        for alias, targets in ALIAS_EXPAND.items():
            if len(alias) >= 3 and (token.startswith(alias) or alias.startswith(token)):
                out.update(targets)
        if token.startswith("binar"):
            out.update(("binaries", "binary"))
        if token.startswith("engin"):
            out.add("engine")
        if "shipping" in token:
            out.add("shipping")
    return sorted(out)


def query_tokens(query: str, chips: list[str] | set[str]) -> list[str]:
    tokens = expand_tokens(tokenize_query(query))
    extra: set[str] = set(tokens)
    for chip in chips:
        extra.update(KEYWORD_TOKENS.get(chip, ()))
    return sorted(extra)


def search_hint(query: str) -> str:
    """Подсказка, если человек написал запрос по-русски."""
    raw = tokenize_query(query)
    mapped = [t for t in raw if t in ALIAS_EXPAND and ALIAS_EXPAND[t]]
    if not mapped:
        return ""
    words = sorted({w for t in mapped for w in ALIAS_EXPAND[t]})
    return "Ищу также: " + ", ".join(words)


def row_haystack(row: dict) -> str:
    parts = [
        row.get("exe", ""),
        row.get("folder", ""),
        row.get("engine", ""),
        row.get("title", "") or "",
    ]
    # Статус из каталога тоже участвует в поиске: чип DLSS находит игры с DLSS-G,
    # даже если в пути нет nvngx_dlss.dll.
    dlssg = row.get("dlssg")
    if dlssg in ("native", "hidden"):
        parts.append("dlss dlssg mfg")
    elif dlssg == "streamline":
        parts.append("dlss dlssg streamline interposer")
    if row.get("online"):
        parts.append("online онлайн")
    return " ".join(p for p in parts if p).lower().replace("\\", " ").replace("/", " ")


def score_row(row: dict, tokens: list[str]) -> tuple[int, list[str]]:
    """Сколько токенов запроса нашлось в пути/имени. Возвращает (счёт, совпадения)."""
    if not tokens:
        base = 2 if row.get("engine") == "Unreal" else 1
        if row.get("dlssg") in ("native", "hidden"):
            base += 1
        return base, []
    hay = row_haystack(row)
    matched = [t for t in tokens if len(t) >= 2 and t in hay]
    if not matched:
        return 0, []
    # Совпадения важнее бонуса каталога — иначе известная игра лезет в любой запрос.
    score = 3 * len(matched)
    if row.get("dlssg") == "native":
        score += 1
    elif row.get("dlssg") == "hidden":
        score += 1
    return score, matched


def filter_rows(
    rows: list[dict],
    query: str,
    chips: list[str] | set[str],
    engine: str = "all",
    only_dlssg: bool = False,
) -> list[int]:
    """Возвращает индексы подходящих строк, отсортированные по релевантности."""
    tokens = query_tokens(query, chips)
    scored: list[tuple[int, int, str]] = []
    for i, row in enumerate(rows):
        if engine != "all" and row.get("engine") != engine:
            continue
        if only_dlssg and row.get("dlssg") not in ("native", "hidden", "streamline"):
            continue
        score, matched = score_row(row, tokens)
        if tokens and score <= 0:
            continue
        row["matched"] = matched
        scored.append((-score, i, row.get("exe", "").lower()))
    scored.sort(key=lambda item: (item[0], item[2]))
    return [i for _, i, _ in scored]


# Системные папки, куда игры не ставятся: пропускаем целиком, иначе скан
# всего диска затянется на десятки минут и упрётся в «Отказано в доступе».
SYSTEM_SKIP_DIRS = {
    "windows",
    "windows.old",
    "winsxs",
    "$recycle.bin",
    "$windows.~bt",
    "$windows.~ws",
    "system volume information",
    "recovery",
    "perflogs",
    "msocache",
    "config.msi",
    "boot",
    "efi",
    "programdata\\packages",
    "node_modules",
    ".git",
    ".svn",
    "__pycache__",
    "appdata\\local\\temp",
    "appdata\\local\\microsoft",
    "appdata\\locallow",
    "windowsapps",
    "packagecache",
    "dotnet",
    "microsoft visual studio",
    "windows kits",
    "android",
    "gradle",
    "temp",
    "tmp",
    "cache",
    "cache2",
    "logs",
    "crashdumps",
    "onedrivetemp",
}


# Те же служебные списки, что и в GUI — держим копию, чтобы модуль был автономным.
SKIP_DIR_PARTS = {
    "easyanticheat",
    "eac",
    "battleye",
    "_commonredist",
    "redist",
    "directx",
    "vcredist",
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

MARKER_DLLS = {
    "unityplayer.dll",
    "gameassembly.dll",
    "nvngx_dlss.dll",
    "nvngx_dlssg.dll",
    "sl.interposer.dll",
    "sl.dlss_g.dll",
}

MIN_GENERIC_EXE_BYTES = 2 * 1024 * 1024


# --------------------------------------------------------------------------
# Глобальный поиск библиотек
# --------------------------------------------------------------------------
_STEAM_LIB_RE = re.compile(r'"path"\s*"([^"]+)"', re.IGNORECASE)


def _reg_values(hive_key_pairs, value_names) -> list[Path]:
    """Достаёт пути из реестра, молча пропуская отсутствующие ключи."""
    out: list[Path] = []
    try:
        import winreg  # type: ignore
    except ImportError:
        return out
    for hive, key in hive_key_pairs:
        try:
            with winreg.OpenKey(hive, key) as handle:
                for name in value_names:
                    try:
                        raw = winreg.QueryValueEx(handle, name)[0]
                    except OSError:
                        continue
                    if raw:
                        out.append(Path(str(raw)))
        except OSError:
            continue
    return out


def _epic_roots() -> list[Path]:
    """Epic хранит путь каждой игры в JSON-манифестах — читаем их все."""
    roots: list[Path] = []
    manifest_dirs = [
        Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
        / "Epic"
        / "EpicGamesLauncher"
        / "Data"
        / "Manifests"
    ]
    try:
        import winreg  # type: ignore

        for path in _reg_values(
            [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Epic Games\EpicGamesLauncher"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Epic Games\EpicGamesLauncher"),
            ],
            ("AppDataPath",),
        ):
            manifest_dirs.append(path / "Manifests")
    except ImportError:
        pass

    import json

    for folder in manifest_dirs:
        if not folder.is_dir():
            continue
        try:
            items = list(folder.glob("*.item"))
        except OSError:
            continue
        for item in items:
            try:
                data = json.loads(item.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, ValueError):
                continue
            location = data.get("InstallLocation") or data.get("ManifestLocation")
            if location:
                path = Path(str(location))
                # Берём родителя: обычно это общая папка библиотеки Epic.
                if path.is_dir():
                    roots.append(path)
    return roots


def _gog_roots() -> list[Path]:
    """GOG Galaxy: путь к каждой игре лежит в отдельном ключе реестра."""
    roots: list[Path] = []
    try:
        import winreg  # type: ignore
    except ImportError:
        return roots
    for hive, base in (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\Games"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\GOG.com\Games"),
    ):
        try:
            with winreg.OpenKey(hive, base) as handle:
                count = winreg.QueryInfoKey(handle)[0]
                for i in range(count):
                    try:
                        sub = winreg.EnumKey(handle, i)
                        with winreg.OpenKey(handle, sub) as game:
                            path = winreg.QueryValueEx(game, "path")[0]
                            if path and Path(path).is_dir():
                                roots.append(Path(path))
                    except OSError:
                        continue
        except OSError:
            continue
    return roots


def _xbox_roots() -> list[Path]:
    """Xbox/Game Pass: на каждом диске лежит .GamingRoot с именем папки игр."""
    roots: list[Path] = []
    for drive in _drive_letters():
        marker = drive / ".GamingRoot"
        try:
            if not marker.is_file():
                continue
            raw = marker.read_bytes()
        except OSError:
            continue
        # Формат: 4 байта сигнатуры + UTF-16LE путь относительно диска.
        try:
            text = raw[4:].decode("utf-16-le", errors="ignore").strip("\x00")
        except Exception:
            continue
        if text:
            candidate = drive / text.strip("\\/")
            if candidate.is_dir():
                roots.append(candidate)
    return roots


def _launcher_roots() -> list[Path]:
    """Прочие лаунчеры через реестр: Ubisoft, EA/Origin, Battle.net, Riot."""
    roots: list[Path] = []
    try:
        import winreg  # type: ignore
    except ImportError:
        return roots
    pairs = [
        ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Ubisoft\Launcher"), ("InstallDir",)),
        ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Origin"), ("ClientPath",)),
        ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Electronic Arts\EA Desktop"), ("InstallLocation",)),
        ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Blizzard Entertainment\Battle.net"), ("InstallPath",)),
        ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Riot Games, Inc"), ("InstallLocation",)),
    ]
    for key, names in pairs:
        for path in _reg_values([key], names):
            folder = path if path.is_dir() else path.parent
            if folder.is_dir():
                roots.append(folder)
            games = folder / "games"
            if games.is_dir():
                roots.append(games)
    return roots


def _steam_roots() -> list[Path]:
    roots: list[Path] = []
    bases: list[Path] = []

    try:
        import winreg  # type: ignore

        for hive, key in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        ):
            try:
                with winreg.OpenKey(hive, key) as handle:
                    for value in ("SteamPath", "InstallPath"):
                        try:
                            path = winreg.QueryValueEx(handle, value)[0]
                            if path:
                                bases.append(Path(path))
                        except OSError:
                            continue
            except OSError:
                continue
    except ImportError:
        pass

    bases.extend(
        [
            Path(r"C:\Program Files (x86)\Steam"),
            Path(r"C:\Program Files\Steam"),
        ]
    )

    for base in bases:
        common = base / "steamapps" / "common"
        if common.is_dir():
            roots.append(common)
        vdf = base / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            try:
                text = vdf.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in _STEAM_LIB_RE.findall(text):
                lib = Path(match.replace("\\\\", "\\")) / "steamapps" / "common"
                if lib.is_dir():
                    roots.append(lib)
    return roots


def _drive_letters() -> list[Path]:
    if os.name != "nt":
        return []
    return [Path(f"{letter}:\\") for letter in string.ascii_uppercase if Path(f"{letter}:\\").exists()]


# Имена папок, которые сами по себе означают «тут лежат игры».
_LIBRARY_DIR_NAMES = {
    "steamapps",
    "steamlibrary",
    "games",
    "игры",
    "game",
    "epic games",
    "gog games",
    "gog galaxy",
    "xboxgames",
    "origin games",
    "ea games",
    "ubisoft game launcher",
    "battle.net",
    "riot games",
    "my games",
}

# Куда не имеет смысла лезть даже при поверхностном обходе.
_CRAWL_SKIP = SYSTEM_SKIP_DIRS | {
    "program files",
    "program files (x86)",
    "users",
    "documents and settings",
    "inetpub",
    "drivers",
    "intel",
    "amd",
}


def _crawl_for_libraries(roots: list[Path], max_depth: int = 4) -> list[Path]:
    """Поверхностный обход дисков в поисках папок-библиотек.

    Не сканирует игры — только ищет, где они лежат: steamapps\\common,
    любые папки Games / Игры / Epic Games / GOG Games на любой глубине до
    max_depth, плюс каталоги, где рядом лежат несколько игровых папок.
    """
    found: list[Path] = []

    def scan(folder: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = [e for e in os.scandir(folder) if e.is_dir(follow_symlinks=False)]
        except (OSError, PermissionError):
            return
        for entry in entries:
            name = entry.name
            low = name.lower()
            if low.startswith("$") or low in SYSTEM_SKIP_DIRS:
                continue
            path = Path(entry.path)

            if low == "steamapps":
                common = path / "common"
                if common.is_dir():
                    found.append(common)
                continue

            if low in _LIBRARY_DIR_NAMES:
                # Для SteamLibrary/Steam берём именно steamapps\common,
                # чтобы не тащить downloading, workshop и shadercache.
                common = path / "steamapps" / "common"
                found.append(common if common.is_dir() else path)
                # Внутрь библиотеки глубже не лезем — её просканирует основной поиск.
                continue

            if depth < max_depth and low not in _CRAWL_SKIP:
                scan(path, depth + 1)

    for root in roots:
        # На верхнем уровне диска в Program Files зайти всё-таки надо:
        # там живут Epic Games, GOG Galaxy, Ubisoft и т.п.
        scan(root, 1)
        for pf in ("Program Files", "Program Files (x86)"):
            pf_path = root / pf
            if pf_path.is_dir():
                try:
                    for entry in os.scandir(pf_path):
                        if not entry.is_dir(follow_symlinks=False):
                            continue
                        low = entry.name.lower()
                        path = Path(entry.path)
                        if low in _LIBRARY_DIR_NAMES or low == "steam":
                            common = path / "steamapps" / "common"
                            found.append(common if common.is_dir() else path)
                except (OSError, PermissionError):
                    pass
    return found


def _drop_nested(paths: list[Path]) -> list[Path]:
    """Убирает вложенные корни: если есть D:\\Games, то D:\\Games\\X не нужен."""
    uniq: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).rstrip("\\/").lower()
        if key and key not in seen:
            seen.add(key)
            uniq.append(path)
    uniq.sort(key=lambda p: len(str(p)))
    result: list[Path] = []
    for path in uniq:
        low = str(path).rstrip("\\/").lower()
        if any(low.startswith(str(kept).rstrip("\\/").lower() + os.sep) for kept in result):
            continue
        result.append(path)
    return result


def library_roots(deep: bool = True) -> list[Path]:
    """Все игровые библиотеки: лаунчеры из реестра + обход дисков.

    deep=False — только быстрые источники (реестр, манифесты), без обхода.
    """
    found: list[Path] = []

    # 1. Точные источники: Steam, Epic, GOG, Xbox, прочие лаунчеры.
    for getter in (_steam_roots, _epic_roots, _gog_roots, _xbox_roots, _launcher_roots):
        try:
            found.extend(getter())
        except Exception:
            continue

    # 2. Обход дисков — находит ручные папки вроде E:\Мои игры\... ,
    #    вторые Steam-библиотеки и всё, что не прописано в реестре.
    if deep:
        try:
            found.extend(_crawl_for_libraries(fixed_drives() or _drive_letters()))
        except Exception:
            pass

    return _drop_nested([p for p in found if p.is_dir()])


def describe_roots(roots: list[Path]) -> str:
    if not roots:
        return "библиотеки не найдены"
    shown = ", ".join(str(r) for r in roots[:3])
    if len(roots) > 3:
        shown += f" и ещё {len(roots) - 3}"
    return shown


# --------------------------------------------------------------------------
# Скан всего ПК
# --------------------------------------------------------------------------
def fixed_drives() -> list[Path]:
    """Локальные (не сетевые и не съёмные) диски."""
    if os.name != "nt":
        return []
    drives: list[Path] = []
    try:
        import ctypes

        get_type = ctypes.windll.kernel32.GetDriveTypeW
        for letter in string.ascii_uppercase:
            root = f"{letter}:\\"
            # 3 = DRIVE_FIXED, 2 = DRIVE_REMOVABLE
            if get_type(root) == 3:
                drives.append(Path(root))
    except Exception:
        drives = [p for p in _drive_letters()]
    return drives


def all_pc_roots(include_removable: bool = False) -> list[Path]:
    """Корни для скана всего компьютера."""
    roots = fixed_drives()
    if include_removable or not roots:
        for drive in _drive_letters():
            if drive not in roots:
                roots.append(drive)
    return roots


def _dir_is_skipped(path: str) -> bool:
    low = path.lower()
    parts = low.replace("/", "\\").split("\\")
    for part in parts:
        if part in SYSTEM_SKIP_DIRS or part in SKIP_DIR_PARTS:
            return True
    for combo in SYSTEM_SKIP_DIRS:
        if "\\" in combo and combo in low:
            return True
    return False


def _is_junk_exe_name(name: str) -> bool:
    low = name.lower()
    return any(part in low for part in SKIP_EXE_PARTS)


def walk_for_exes(
    roots: list[Path],
    mode: str = "any",
    on_progress=None,
    should_stop=None,
    progress_every: int = 400,
) -> list[Path]:
    """Один проход по дереву каталогов вместо десятка rglob.

    mode: "ue" — только *-Win64-Shipping.exe
          "any" — Shipping + папки с маркерами движка/DLSS + крупные .exe
          "all" — любые неслужебные .exe
    on_progress(dirs_done, found, current_path) — колбэк для статуса.
    should_stop() -> bool — досрочная остановка.
    """
    results: list[Path] = []
    seen: set[str] = set()
    dirs_done = 0

    def add(path: Path) -> None:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            results.append(path)

    for root in roots:
        for dirpath, dirnames, filenames in os.walk(str(root), topdown=True, onerror=lambda e: None):
            if should_stop is not None and should_stop():
                return results

            # Обрезаем ветки целиком — это и даёт скорость на полном скане.
            dirnames[:] = [
                d
                for d in dirnames
                if not d.startswith("$")
                and d.lower() not in SYSTEM_SKIP_DIRS
                and d.lower() not in SKIP_DIR_PARTS
            ]

            dirs_done += 1
            if on_progress is not None and dirs_done % progress_every == 0:
                on_progress(dirs_done, len(results), dirpath)

            if _dir_is_skipped(dirpath):
                continue

            exe_names = [f for f in filenames if f.lower().endswith(".exe")]
            if not exe_names:
                continue

            folder = Path(dirpath)

            if mode == "ue":
                for name in exe_names:
                    if name.lower().endswith("-win64-shipping.exe"):
                        add(folder / name)
                continue

            if mode == "all":
                for name in exe_names:
                    if not _is_junk_exe_name(name):
                        add(folder / name)
                continue

            # mode == "any"
            shipping = [n for n in exe_names if n.lower().endswith("-win64-shipping.exe")]
            for name in shipping:
                add(folder / name)

            lower_files = {f.lower() for f in filenames}
            has_marker = bool(lower_files & MARKER_DLLS)
            if has_marker:
                pick = _pick_main_exe_name(folder, exe_names)
                if pick:
                    add(folder / pick)

            if not shipping:
                for name in exe_names:
                    if _is_junk_exe_name(name):
                        continue
                    try:
                        if (folder / name).stat().st_size >= MIN_GENERIC_EXE_BYTES:
                            add(folder / name)
                    except OSError:
                        continue

    if on_progress is not None:
        on_progress(dirs_done, len(results), "")
    return results


def _pick_main_exe_name(folder: Path, exe_names: list[str]) -> str | None:
    best = None
    best_size = 0
    for name in exe_names:
        if _is_junk_exe_name(name):
            continue
        if name.lower().endswith("-win64-shipping.exe"):
            return name
        try:
            size = (folder / name).stat().st_size
        except OSError:
            continue
        if size > best_size:
            best = name
            best_size = size
    return best
