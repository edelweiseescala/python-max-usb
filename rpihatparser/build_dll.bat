@echo off
REM

echo Building rpi_hat_parser.dll...

REM
gcc -Wall -Wextra -O2 -std=c99 -c rpi_hat_parser.c -o rpi_hat_parser.o

if %ERRORLEVEL% NEQ 0 (
    echo Compilation failed!
    exit /b 1
)

echo Compilation successful, linking DLL...

REM
gcc -shared -o rpi_hat_parser.dll rpi_hat_parser.o

if %ERRORLEVEL% NEQ 0 (
    echo Linking failed!
    exit /b 1
)

echo Successfully built rpi_hat_parser.dll

REM
del rpi_hat_parser.o
