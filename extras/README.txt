Папка extras
============

Сюда кладутся дополнительные DLL, которые установщик копирует
в папку игры вместе с выбранными анлоками.

Подпапки
--------
extras\           — общие файлы (как раньше)
extras\fsr3\      — AMD FSR 3 Frame Generation
extras\xess\      — Intel XeSS Frame Generation (XeFG)
extras\optiscaler — OptiScaler.dll / OptiScaler.ini

Что имеет смысл класть самостоятельно
(в архив не входят — возьмите с официальных страниц проектов):

FSR 3
  amd_fidelityfx_dx12.dll
  или amd_fidelityfx_loader_dx12.dll + amd_fidelityfx_framegeneration_dx12.dll
  dlssg_to_fsr3_amd_is_better.dll   (Nukem, для игр с DLSS-G)

XeSS / XeFG
  libxess_fg.dll
  libxell.dll
  libxess.dll

OptiScaler
  OptiScaler.dll   (установщик переименует в dxgi.dll, если имя свободно)
  fakenvapi.dll, nvngx.dll — по инструкции OptiScaler

Не кладите сразу несколько прокси с разными именами
(version + dxgi + winmm) вручную. Установщик сам разведёт:
  DLSS MFG  → выбранный прокси (по умолчанию version.dll)
  OptiScaler → dxgi.dll (или другое имя, если version уже занят)

Подпапки сохраняются. При удалении мода снимутся только
скопированные файлы, оригиналы вернутся из .mfgbak.
