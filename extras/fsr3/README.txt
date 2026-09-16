extras\fsr3 — AMD FSR 3 Frame Generation
========================================

Положите сюда DLL FidelityFX / Nukem. Установщик скопирует их
в папку игры, если включён анлок «FSR 3».

Рекомендуемый набор (официальные сборки OptiScaler / GPUOpen / Nukem):
  amd_fidelityfx_dx12.dll
  dlssg_to_fsr3_amd_is_better.dll

Даже без этих файлов установщик запишет:
  OptiScaler.ini с FGOutput=fsrfg
  auto_mfg_Engine.ini — нативный анлок r.FidelityFX.FI.Enabled для Unreal
  и попытается вписать те же ключи в Engine.ini в %LOCALAPPDATA%.
