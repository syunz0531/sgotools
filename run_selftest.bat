@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===============================================
echo  sgotools install + self test
echo ===============================================
echo.
where python >nul 2>nul
if %errorlevel%==0 (set PY=python) else (set PY=py)

echo [1/3] installing package...
%PY% -m pip install -e . --quiet
if errorlevel 1 (
  echo    install FAILED - see messages above
  pause
  exit /b 1
)
echo    done
echo.

echo [2/3] running tests...
%PY% -m pip install pytest --quiet
%PY% -m pytest tests -q
echo.

echo [3/3] live download self test...
%PY% selftest.py
echo.
pause
