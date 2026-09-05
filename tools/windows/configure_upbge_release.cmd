@echo off
setlocal

call "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64
if errorlevel 1 exit /b %errorlevel%

"C:\Users\azoo\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\cmake.exe" ^
  -S "C:\Users\azoo\git\upbge" ^
  -B "C:\Users\azoo\git\build_upbge_windows_Release_x64_vc17_Release" ^
  -G Ninja ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DLIBDIR="C:/Users/azoo/git/blender/lib/windows_x64" ^
  -DWITH_XR_OPENXR=ON ^
  -DWITH_GAMEENGINE=ON ^
  -DWITH_PLAYER=ON ^
  -DCMAKE_INSTALL_PREFIX="C:/Users/azoo/git/build_upbge_windows_Release_x64_vc17_Release/bin"

exit /b %errorlevel%
