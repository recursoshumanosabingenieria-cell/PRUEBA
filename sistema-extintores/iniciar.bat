@echo off
echo ========================================
echo Sistema de Inventario - AB Ingenieria
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist "venv\" (
    echo Creando entorno virtual...
    python -m venv venv
    echo.
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Verificar si las dependencias están instaladas
if not exist "venv\Lib\site-packages\flask\" (
    echo Instalando dependencias...
    pip install -r requirements.txt
    echo.
)

REM Iniciar la aplicación
echo Iniciando servidor...
echo.
echo La aplicacion estara disponible en: http://localhost:5000
echo Usuario: admin
echo Contrasena: admin123
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

python app.py

pause
