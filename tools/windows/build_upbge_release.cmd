@echo off
setlocal

call "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64
if errorlevel 1 exit /b %errorlevel%

"C:\Users\azoo\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\cmake.exe" ^
  --build "C:\Users\azoo\git\build_upbge_windows_Release_x64_vc17_Release" ^
  --target blender ^
  --parallel 4

exit /b %errorlevel%
