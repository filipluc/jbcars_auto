@echo off
call c:\Github\openchrome.bat

pushd c:\Github\jbcars_auto

git reset --hard HEAD
git pull origin master

c:\Github\jbcars_auto\venv\Scripts\python.exe main.py

popd

TASKKILL /IM chrome.exe /F
