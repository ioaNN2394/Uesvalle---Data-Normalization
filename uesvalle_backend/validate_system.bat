@echo off
REM ====================================================================
REM Script de Validación Completa del Sistema UESValle ETL Backend
REM ====================================================================
REM
REM Este script ejecuta una validación completa del sistema incluyendo:
REM - Verificación de dependencias
REM - Pruebas rápidas del sistema
REM - Suite completa de tests
REM - Validación de endpoints API
REM - Verificación de configuración
REM
REM Uso: validate_system.bat
REM ====================================================================

title Validación Sistema UESValle ETL Backend

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                 VALIDACIÓN SISTEMA UESVALLE ETL                ║
echo ║                        Backend Django                          ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo ⏰ Iniciado: %DATE% %TIME%
echo 🏠 Directorio: %CD%
echo.

REM ====================================================================
REM 1. Verificar que estamos en el directorio correcto
REM ====================================================================
echo 📂 Verificando estructura de proyecto...

if not exist "manage.py" (
    echo ❌ Error: manage.py no encontrado. 
    echo    Asegurate de ejecutar este script desde el directorio raíz del proyecto.
    pause
    exit /b 1
)

if not exist "apps" (
    echo ❌ Error: Directorio 'apps' no encontrado.
    echo    Estructura de proyecto incorrecta.
    pause
    exit /b 1
)

if not exist ".env" (
    echo ⚠️  Advertencia: Archivo .env no encontrado.
    echo    Algunas pruebas podrían fallar sin configuración de entorno.
    echo.
)

echo ✅ Estructura de proyecto verificada

REM ====================================================================
REM 2. Verificar entorno Python y dependencias
REM ====================================================================
echo.
echo 🐍 Verificando entorno Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python no está instalado o no está en PATH
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ %PYTHON_VERSION% detectado

echo.
echo 📦 Verificando dependencias...
pip check
if %errorlevel% neq 0 (
    echo ❌ Error: Dependencias con conflictos detectadas
    echo.
    echo 🔧 Intentando instalar/actualizar dependencias...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Error instalando dependencias
        pause
        exit /b 1
    )
)
echo ✅ Dependencias verificadas

REM ====================================================================
REM 3. Ejecutar pruebas rápidas
REM ====================================================================
echo.
echo ⚡ Ejecutando pruebas rápidas del sistema...
echo ────────────────────────────────────────────────────────────────

python quick_test.py
set QUICK_TEST_RESULT=%errorlevel%

if %QUICK_TEST_RESULT% neq 0 (
    echo.
    echo ⚠️  Las pruebas rápidas detectaron problemas.
    echo    ¿Deseas continuar con la validación completa? (S/N)
    set /p continue="Continuar: "
    if /i not "%continue%"=="S" (
        echo Validación cancelada por el usuario.
        pause
        exit /b 1
    )
) else (
    echo ✅ Pruebas rápidas completadas exitosamente
)

REM ====================================================================
REM 4. Ejecutar suite completa de tests
REM ====================================================================
echo.
echo 🧪 Ejecutando suite completa de tests Django...
echo ────────────────────────────────────────────────────────────────

python manage.py test tests/ --verbosity=2
set DJANGO_TEST_RESULT=%errorlevel%

if %DJANGO_TEST_RESULT% neq 0 (
    echo ❌ Suite de tests Django falló
    echo    Revisar errores anteriores para más detalles.
) else (
    echo ✅ Suite de tests Django completada exitosamente
)

REM ====================================================================
REM 5. Verificar migraciones
REM ====================================================================
echo.
echo 🗃️  Verificando estado de migraciones...

python manage.py showmigrations --plan > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error verificando migraciones
) else (
    echo ✅ Migraciones verificadas
)

REM ====================================================================
REM 6. Verificar configuración de archivos estáticos (opcional)
REM ====================================================================
echo.
echo 📁 Verificando archivos estáticos...

python manage.py collectstatic --dry-run --noinput > nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Advertencia: Problema con archivos estáticos (no crítico para ETL)
) else (
    echo ✅ Archivos estáticos OK
)

REM ====================================================================
REM 7. Test de servidor de desarrollo (opcional)
REM ====================================================================
echo.
echo 🌐 ¿Deseas probar el servidor de desarrollo? (S/N)
echo    (Se iniciará el servidor por 10 segundos para verificar que funciona)
set /p test_server="Probar servidor: "

if /i "%test_server%"=="S" (
    echo.
    echo Iniciando servidor de desarrollo...
    echo Servidor se detendrá automáticamente en 10 segundos.
    echo.
    
    REM Iniciar servidor en segundo plano y detenerlo después de 10 segundos
    start /b python manage.py runserver 127.0.0.1:8000
    timeout /t 10 /nobreak > nul
    
    REM Intentar conectar al servidor
    curl -s http://127.0.0.1:8000/api/etl/health/ > nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Servidor de desarrollo funciona correctamente
    ) else (
        echo ⚠️  No se pudo verificar el servidor (curl no disponible o servidor no respondió)
    )
    
    REM Detener servidor
    taskkill /f /im python.exe > nul 2>&1
)

REM ====================================================================
REM 8. Resumen final
REM ====================================================================
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                      RESUMEN DE VALIDACIÓN                     ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

set TOTAL_ERRORS=0

REM Calcular puntuación final
if %QUICK_TEST_RESULT% neq 0 (
    echo ❌ Pruebas rápidas: FALLIDAS
    set /a TOTAL_ERRORS+=1
) else (
    echo ✅ Pruebas rápidas: EXITOSAS
)

if %DJANGO_TEST_RESULT% neq 0 (
    echo ❌ Suite de tests Django: FALLIDAS  
    set /a TOTAL_ERRORS+=1
) else (
    echo ✅ Suite de tests Django: EXITOSAS
)

echo.
if %TOTAL_ERRORS% equ 0 (
    echo 🎉 ¡VALIDACIÓN COMPLETADA EXITOSAMENTE!
    echo.
    echo ✨ El sistema UESValle ETL Backend está listo para usar.
    echo.
    echo 🚀 Próximos pasos recomendados:
    echo    • Iniciar servidor: python manage.py runserver
    echo    • Acceder a admin: http://localhost:8000/admin/
    echo    • Probar API: http://localhost:8000/api/etl/health/
    echo    • Ejecutar ETL: python manage.py etl_run --dry-run
    echo.
    echo 📚 Documentación adicional en DEPLOYMENT.md
) else (
    echo ⚠️  VALIDACIÓN COMPLETADA CON %TOTAL_ERRORS% ERROR(S)
    echo.
    echo 🔧 Acciones recomendadas:
    echo    • Revisar errores mostrados anteriormente
    echo    • Verificar configuración en .env
    echo    • Consultar DEPLOYMENT.md para troubleshooting
    echo    • Re-ejecutar validación después de correcciones
    echo.
    echo 📞 Para soporte:
    echo    • Revisar logs detallados en terminal
    echo    • Consultar documentación del proyecto
)

echo.
echo ⏰ Completado: %DATE% %TIME%
echo.

REM Preguntar si quiere ver un comando de ayuda
echo ❓ ¿Mostrar comandos útiles adicionales? (S/N)
set /p show_commands="Mostrar comandos: "

if /i "%show_commands%"=="S" (
    echo.
    echo ╔════════════════════════════════════════════════════════════════╗
    echo ║                     COMANDOS ÚTILES                            ║
    echo ╚════════════════════════════════════════════════════════════════╝
    echo.
    echo 🧪 Testing:
    echo    python quick_test.py                    - Pruebas rápidas
    echo    python manage.py test                   - Tests completos
    echo    python manage.py test tests.test_models - Solo tests de modelos
    echo.
    echo 🗃️  Base de datos:
    echo    python manage.py dbshell                - Consola de BD
    echo    python manage.py showmigrations         - Estado migraciones
    echo    python manage.py migrate                - Aplicar migraciones
    echo.
    echo 🔧 Desarrollo:
    echo    python manage.py shell                  - Shell Django
    echo    python manage.py runserver              - Servidor desarrollo
    echo    python manage.py collectstatic          - Archivos estáticos
    echo.
    echo 🚀 ETL:
    echo    python manage.py etl_run --dry-run      - ETL modo prueba
    echo    python manage.py etl_run                - ETL completo
    echo.
)

echo.
pause
exit /b %TOTAL_ERRORS%