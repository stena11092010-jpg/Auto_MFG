Если хотите поддержать автора и повысить мотивацию в развитии программы:  https://dalink.to/alexander_shc



В данный момент исходный код неправильный. Скачайте последний релиз в формате zip, это те же исходники.

Auto МФГ — графический установщик  v1.3
=======================================

Что это
-------
Программа ставит анлок генерации кадров рядом с игровым EXE.

  NVIDIA DLSS MFG     version.dll + dlssg_sm86.ini
  AMD FSR 3 FG        OptiScaler.ini (FGOutput=fsrfg) + Engine.ini Unreal
  Intel XeSS / XeFG   OptiScaler.ini (UnlockMFG) + DilateMotionVectors=0

Подходят Unreal Engine, Unity, REDengine и другие. Мод нужно класть
в папку того EXE, который реально запускает рендер.

Как запустить
-------------
1. Нужен Python 3 (https://www.python.org/downloads/).
   При установке включите «Add python.exe to PATH».
2. Дважды щёлкните «Запустить.bat»
   или выполните:  python auto_mfg_gui.py

Как пользоваться
----------------
1. «Папка…» — каталог игры или Steam\steamapps\common
   либо «Указать EXE…» — сразу выбрать игровой exe.
2. Режим поиска:
   • Любые игры — UE + Unity + папки с DLSS/FSR/XeSS + крупные .exe
   • Только Unreal — *-Win64-Shipping.exe
   • Все .exe — широкий поиск без служебных установщиков
3. Анлок генераций — галочки:
   • DLSS MFG — нативный SM86 (как в 1.2)
   • FSR 3 FG — ini-анлок + extras\fsr3
   • XeSS FG  — XeFG UnlockMFG + extras\xess
   Если включены FSR и XeSS сразу, «Основной выход FG» выбирает,
   что прописать в OptiScaler.ini (FGOutput=fsrfg или xefg).
4. Если игра не подхватывает version.dll, смените
   «Имя прокси-DLL» на winmm / dxgi / dbghelp / dinput8 / winhttp.
   OptiScaler при этом ставится отдельно как dxgi.dll.
5. Если в меню игры нет пункта генерации кадров —
   включите «Игра без пункта генерации кадров» и выберите 2× / 3× / 4×.
6. «Установить мод» или «Удалить мод».

FSR 3
-----
• Unreal: установщик пишет r.FidelityFX.FI.Enabled в Engine.ini
  (%LOCALAPPDATA%\<Игра>\Saved\Config\Windows) и дублирует ключи
  в auto_mfg_Engine.ini рядом с EXE.
• Для игр без нативного FSR-FG положите в extras\fsr3
  amd_fidelityfx_dx12.dll и/или dlssg_to_fsr3_amd_is_better.dll,
  в extras\optiscaler — OptiScaler.dll.
• В игре: апскейлер FSR 3, VSync выкл, без cap FPS.

XeSS / XeFG
-----------
• UnlockMFG=true и MaxInterpolatedFrames в OptiScaler.ini.
• Unreal: r.NGX.DLSS.DilateMotionVectors=0.
• Нужны libxess_fg.dll и libxell.dll (extras\xess) + OptiScaler.
• Только borderless / windowed fullscreen. Не Vulkan, не exclusive
  fullscreen, не HDR16/scRGB.

Игры без переключателя
----------------------
Галочка помогает, когда пункт скрыт или серый.
DLSS-пакет сам НЕ добавляет генерацию туда, где DLSS-G нет.
FSR 3 / XeSS через OptiScaler (extras\optiscaler) как раз для таких тайтлов.

Важно
-----
- version.dll и dlssg_sm86.ini должны лежать рядом со скриптом,
  если ставите DLSS MFG.
- FSR 3 и XeSS можно ставить без version.dll — достаточно ini-анлока.
- Если в папке игры уже был свой version.dll (или другой прокси),
  программа сохранит его как *.mfgbak и вернёт при удалении.
- После правки ini полностью перезапустите игру.
- Не используйте в онлайне, где сторонние DLL запрещены.
- Ставьте только один прокси на технологию: DLSS → выбранное имя,
  OptiScaler → dxgi.dll.

Настройки ini (DLSS)
--------------------
Router=SM86          — Ampere и новее; для Turing попробуйте SM75
KernelImage=PTX
HardwareBilinear=0
MaxGeneratedFrames=3 — потолок 2x/3x/4x (1/2/3)
Level=1              — уровень лога
