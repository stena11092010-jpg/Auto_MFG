extras\xess — Intel XeSS Frame Generation (XeFG)
================================================

Положите сюда DLL XeSS FG. Установщик скопирует их
в папку игры, если включён анлок «XeSS».

Рекомендуемый набор (SDK Intel / сборка OptiScaler):
  libxess_fg.dll
  libxell.dll
  libxess.dll

Даже без этих файлов установщик запишет:
  OptiScaler.ini с FGOutput=xefg, UnlockMFG=true
  auto_mfg_Engine.ini — DilateMotionVectors=0 и r.XessFG.Enabled
  и попытается вписать те же ключи в Engine.ini в %LOCALAPPDATA%.

XeFG: только borderless, не exclusive fullscreen, не Vulkan, не HDR16/scRGB.
