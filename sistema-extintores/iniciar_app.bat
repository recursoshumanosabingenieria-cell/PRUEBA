@echo off
echo ============================================
echo   SISTEMA DE GESTION DE EXTINTORES
echo ============================================
echo.
echo Iniciando aplicacion...
echo.

REM Verificar si Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado
    echo Por favor instale Python desde https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Verificar si las dependencias estan instaladas
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias por primera vez...
    echo Esto puede tardar unos minutos...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: No se pudieron instalar las dependencias
        pause
        exit /b 1
    )
)

REM Ejecutar la aplicacion
python app.py

pause
