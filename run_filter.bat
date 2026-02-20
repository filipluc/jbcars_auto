@echo off
@REM call c:\Github\openchrome.bat
@REM For running less cars, update Filter with cars in main.py
pushd c:\Github\jbcars_auto


c:\Github\jbcars_auto\venv\Scripts\python.exe main.py

popd

TASKKILL /IM chrome.exe /F
