@echo off
chcp 65001 >nul
echo ============================================================
echo   Downloading Embedding Model for Wavescan
echo ============================================================
echo.

cd /d "%~dp0"

set "MODEL_DIR=log_ai_agent\ai_agent_v2\embedding\models\multilingual-e5-base"
set "HF_CACHE=%USERPROFILE%\.cache\huggingface\models--intfloat--multilingual-e5-base"

echo [1/2] Setting up model directory...
if not exist "log_ai_agent\ai_agent_v2\embedding\models" (
    mkdir "log_ai_agent\ai_agent_v2\embedding\models"
)
if exist "%MODEL_DIR%" (
    echo   Model already exists at: %MODEL_DIR%
    echo   To re-download, delete the folder and run this script again.
    echo.
    echo SUCCESS! Model is ready.
    pause
    exit /b 0
)
mkdir "%MODEL_DIR%"

echo.
echo [2/2] Checking for cached model...

rem Check if model exists in HF cache
if exist "%HF_CACHE%\refs\main" (
    echo   Found in HF cache! Copying...
    for /f "tokens=*" %%C in ('type "%HF_CACHE%\refs\main"') do set COMMIT=%%C
    xcopy /E /I /Y "%HF_CACHE%\snapshots\%COMMIT%\*" "%MODEL_DIR%" >nul
    if %errorlevel% equ 0 (
        echo   Done! Model copied from cache.
        echo.
        echo ============================================================
        echo   SUCCESS! Model ready from cache.
        echo   Location: %MODEL_DIR%
        echo ============================================================
        pause
        exit /b 0
    )
)

echo   Not in cache. Downloading from HuggingFace...
echo   This may take a few minutes. Model size: ~1.1 GB
echo.

uv run hf download intfloat/multilingual-e5-base --local-dir "%MODEL_DIR%"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Model download failed!
    echo.
    echo Possible causes:
    echo   1. HuggingFace API rate limit (429) - wait a few minutes
    echo   2. No internet connection
    echo   3. Authentication required - run: hf login
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   SUCCESS! Model downloaded and ready.
echo   Location: %MODEL_DIR%
echo ============================================================
echo.
pause
