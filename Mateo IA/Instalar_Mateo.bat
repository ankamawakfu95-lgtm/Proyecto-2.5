@echo off
chcp 65001 >nul
title Mateo AI Ultra - Instalador
cd /d "%~dp0"
cls
echo.
echo â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
echo â•‘                                                              â•‘
echo â•‘           ðŸ¤– MATEO AI ULTRA - Instalador                     â•‘
echo â•‘                                                              â•‘
echo â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
echo.
:: Verificar Python
echo ðŸ” Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo âŒ Python no estÃ¡ instalado
    echo.
    echo Por favor instala Python 3.8 o superior:
    echo https://www.python.org/downloads/
    echo.
    echo âš ï¸  IMPORTANTE: Marca "Add Python to PATH" durante la instalaciÃ³n
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo âœ… Python %PYTHON_VERSION% detectado
echo.
:: Verificar Node.js
echo ðŸ” Verificando Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo âŒ Node.js no estÃ¡ instalado
    echo.
    echo Por favor instala Node.js 16 o superior:
    echo https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=1" %%a in ('node --version') do set NODE_VERSION=%%a
echo âœ… Node.js %NODE_VERSION% detectado
echo.
:: Crear entorno virtual
echo ðŸ“¦ Creando entorno virtual Python...
if exist "venv" (
    echo    Entorno virtual ya existe, omitiendo...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo âŒ Error creando entorno virtual
        pause
        exit /b 1
    )
    echo âœ… Entorno virtual creado
)
echo.
:: Activar entorno virtual
call venv\Scripts\activate.bat
:: Actualizar pip
echo â¬†ï¸  Actualizando pip...
python -m pip install --upgrade pip -q
echo âœ… Pip actualizado
echo.
:: Instalar dependencias de Python
echo ðŸ“¥ Instalando dependencias de Python...
echo    Esto puede tomar varios minutos...
echo.
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo âŒ Error instalando dependencias de Python
    pause
    exit /b 1
)
echo âœ… Dependencias de Python instaladas
echo.
:: Descargar modelos de HuggingFace
echo ðŸ§  Descargando modelos de lenguaje...
echo    (Esta operaciÃ³n puede tardar varios minutos...)
cd backend
python -c "from neural.language_model import NeuralLanguageProcessor; NeuralLanguageProcessor()" 2>nul
cd ..
echo âœ… Modelos descargados
echo.
:: Instalar dependencias de Node.js
echo ðŸ“¥ Instalando dependencias del frontend...
if exist "frontend" (
    cd frontend
    if exist "package.json" (
        call npm install
        if errorlevel 1 (
            echo âŒ Error instalando dependencias de Node.js
            pause
            exit /b 1
        )
        echo âœ… Dependencias del frontend instaladas
    ) else (
        echo âš ï¸  No se encontrÃ³ package.json en frontend
    )
    cd ..
) else (
    echo âš ï¸  Directorio frontend no encontrado
)
echo.
:: Crear directorios necesarios
echo ðŸ“ Creando estructura de directorios...
if not exist "data" mkdir data
if not exist "data\vectors" mkdir data\vectors
if not exist "data\conversations" mkdir data\conversations
if not exist "logs" mkdir logs
echo âœ… Directorios creados
echo.
:: Crear archivo .env si no existe
if not exist ".env" (
    echo âš™ï¸  Creando archivo de configuraciÃ³n...
    (
        echo # API Keys para Mateo AI Ultra
        echo # ObtÃ©n tus claves gratuitas en:
        echo # - Wolfram Alpha: https://products.wolframalpha.com/api/
        echo # - NewsAPI: https://newsapi.org/
        echo # - OpenWeather: https://openweathermap.org/api
        echo.
        echo WOLFRAM_ALPHA_APP_ID=
        echo NEWSAPI_KEY=
        echo OPENWEATHER_KEY=
        echo.
        echo # ConfiguraciÃ³n del modelo
        echo MATEO_MODEL=microsoft/DialoGPT-medium
        echo MATEO_USE_GPU=false
    ) > .env
    echo âœ… Archivo .env creado
    echo    EdÃ­talo para agregar tus API keys opcionales
) else (
    echo âœ… Archivo .env ya existe
)
echo.
:: Crear acceso directo en el escritorio
echo ðŸ–¥ï¸  Creando acceso directo...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Mateo AI Ultra.lnk'); $Shortcut.TargetPath = '%~dp0Iniciar_Mateo.bat'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.IconLocation = '%SystemRoot%\System32\SHELL32.dll,13'; $Shortcut.Save()" 2>nul
if errorlevel 1 (
    echo âš ï¸  No se pudo crear acceso directo
) else (
    echo âœ… Acceso directo creado en el escritorio
)
echo.
:: InstalaciÃ³n completada
echo â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
echo.
echo ðŸŽ‰ Â¡INSTALACIÃ“N COMPLETADA!
echo.
echo Para iniciar Mateo AI Ultra:
echo    1. Haz doble clic en "Iniciar_Mateo.bat"
echo    2. O usa el acceso directo en tu escritorio
echo.
echo ðŸ“– DocumentaciÃ³n:
echo    - README.md para mÃ¡s informaciÃ³n
echo    - .env para configurar API keys
echo.
echo ðŸ’¡ Consejo: Agrega tus API keys en el archivo .env
echo    para habilitar todas las funcionalidades.
echo.
pause
exit /b 0
