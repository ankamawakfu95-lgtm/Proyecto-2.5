@echo off
cd /d "%~dp0"
chcp 65001 >nul
title Mateo AI Ultra - Iniciando...
cls
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║              🤖 MATEO AI ULTRA v2.0                          ║
echo ║                                                              ║
echo ║   Red Neuronal + Embeddings Vectoriales + APIs Externas     ║
echo ║                                                              ║
echo ║              Creado por: Leonardo                            ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
:: Verificar Python
echo 🔍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python no está instalado o no está en el PATH
    echo Por favor instala Python 3.8 o superior desde https://python.org
    pause
    exit /b 1
)
echo ✅ Python detectado
echo.
:: Crear entorno virtual si no existe
if not exist "venv" (
    echo 📦 Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Error creando entorno virtual
        pause
        exit /b 1
    )
    echo ✅ Entorno virtual creado
) else (
    echo ✅ Entorno virtual encontrado
)
echo.
:: Activar entorno virtual
echo 🔄 Activando entorno virtual...
call venv\Scripts\activate.bat
:: Instalar dependencias
echo 📥 Instalando/Actualizando dependencias...
echo    (Esto puede tomar unos minutos la primera vez...)
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
)
echo ✅ Dependencias listas
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
:: Opciones de inicio
echo 🚀 Selecciona modo de inicio:
echo.
echo    [1] 🖥️  Solo Interfaz Web (Recomendado)
echo    [2] 💻 Solo Terminal
echo    [3] 🌐 Web + Terminal (Completo)
echo    [4] ⚙️  Configurar API Keys
echo.
set /p opcion="Elige una opción (1-4): "
if "%opcion%"=="1" goto web
if "%opcion%"=="2" goto terminal
if "%opcion%"=="3" goto completo
if "%opcion%"=="4" goto config
goto web

:web
echo.
echo 🌐 Iniciando interfaz web...
echo    La aplicación se abrirá automáticamente en tu navegador
echo    URL: http://localhost:8000/ui
echo.
cd backend
start python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
timeout /t 3 >nul
cd ..
if exist "frontend\package.json" (
    cd frontend
    start npm run dev
    timeout /t 5 >nul
    start http://localhost:5173
) else (
    start http://localhost:8000/ui
)
echo.
echo ✅ Mateo está corriendo!
echo    Presiona cualquier tecla para detener...
pause >nul
goto end

:terminal
echo.
echo 💻 Iniciando modo terminal...
echo.
cd backend
python main.py
goto end

:completo
echo.
echo 🌐 Iniciando modo completo...
echo.
start cmd /k "cd /d %~dp0backend && python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 >nul
if exist "frontend\package.json" (
    start cmd /k "cd /d %~dp0frontend && npm run dev"
    timeout /t 5 >nul
    start http://localhost:5173
) else (
    start http://localhost:8000/ui
)
echo.
echo ✅ Mateo está corriendo en modo completo!
echo    - API: http://localhost:8000
echo    - UI: http://localhost:8000/ui
echo.
pause
goto end

:config
echo.
echo ⚙️  Configuración de API Keys
echo.
echo Estas claves son opcionales pero habilitan funcionalidades adicionales:
echo.
set /p wolfram="Wolfram Alpha App ID (opcional): "
set /p newsapi="NewsAPI Key (opcional): "
set /p weather="OpenWeather API Key (opcional): "
(
    echo # API Keys para Mateo AI Ultra
    echo WOLFRAM_ALPHA_APP_ID=%wolfram%
    echo NEWSAPI_KEY=%newsapi%
    echo OPENWEATHER_KEY=%weather%
) > .env
echo.
echo ✅ Configuración guardada en .env
echo.
pause
goto end

:end
echo.
echo 👋 Cerrando Mateo AI Ultra...
call venv\Scripts\deactivate.bat >nul 2>&1
echo Puedes cerrar las ventanas de Mateo cuando termines.
exit /b 0