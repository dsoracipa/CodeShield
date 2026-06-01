@echo off
setlocal
set ANTLR_JAR=C:\antlr\antlr-4.13.1-complete.jar

if not exist %ANTLR_JAR% (
    echo ERROR: no se encuentra %ANTLR_JAR%
    echo Descargar de https://www.antlr.org/download/antlr-4.13.1-complete.jar
    exit /b 1
)

echo Generando parser ANTLR para Python 3...
cd grammar
java -jar %ANTLR_JAR% -Dlanguage=Python3 -visitor -listener -o ..\generated PythonLexer.g4 PythonParser.g4

if errorlevel 1 (
    echo ERROR: generacion fallida
    cd ..
    exit /b 1
)

cd ..
copy grammar\PythonLexerBase.py generated\PythonLexerBase.py >nul
copy grammar\PythonParserBase.py generated\PythonParserBase.py >nul

REM Crear __init__.py vacio para que generated sea un paquete
echo. > generated\__init__.py

echo OK. Parser generado en /generated
endlocal
