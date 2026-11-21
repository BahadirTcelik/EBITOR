@echo off
rem EE463 - checks of the PCB (placement draft or routed board). Double-click this file.
rem 1) KiCad design rule check  -> out\drc.rpt (and out\drc.json)
rem 2) Course PCB-Checker       -> out\pcb_check.html, out\pcb_check_console.txt
rem The board file is not modified. PCB-Checker is expected in ..\PCB-Checker (copy of
rem github.com/odtu/EE463, "Hardware Project/PCB-Checker").
setlocal EnableExtensions
cd /d "%~dp0"
set "KICAD="
if exist "C:\Program Files\KiCad\8.0\bin\kicad-cli.exe" set "KICAD=C:\Program Files\KiCad\8.0"
if exist "C:\Program Files\KiCad\9.0\bin\kicad-cli.exe" set "KICAD=C:\Program Files\KiCad\9.0"
if exist "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" set "KICAD=C:\Program Files\KiCad\10.0"
if not defined KICAD goto :nokicad
set "CLI=%KICAD%\bin\kicad-cli.exe"
set "PCB=ee463_dcdc.kicad_pcb"
if not exist "%PCB%" goto :nopcb
if not exist out mkdir out
"%CLI%" version > out\kicad_version.txt 2>&1

echo [1/2] KiCad DRC ...
"%CLI%" pcb drc --severity-all --units mm --refill-zones --schematic-parity --format report --output out\drc.rpt "%PCB%" > out\drc_console.txt 2>&1
if errorlevel 1 "%CLI%" pcb drc --severity-all --units mm --refill-zones --format report --output out\drc.rpt "%PCB%" >> out\drc_console.txt 2>&1
if errorlevel 1 "%CLI%" pcb drc --severity-all --units mm --format report --output out\drc.rpt "%PCB%" >> out\drc_console.txt 2>&1
"%CLI%" pcb drc --severity-all --units mm --refill-zones --schematic-parity --format json --output out\drc.json "%PCB%" >> out\drc_console.txt 2>&1

echo [2/2] PCB-Checker ...
set "PY=%KICAD%\bin\python.exe"
if not exist "%PY%" set "PY=python"
set "CHK=..\PCB-Checker\check_pcb.py"
if not exist "%CHK%" goto :nochecker
"%PY%" "%CHK%" "%PCB%" --overload -o out\pcb_check.html > out\pcb_check_console.txt 2>&1
type out\pcb_check_console.txt

echo.
echo Done. Results are in the "out" folder:
echo   drc.rpt, drc.json, pcb_check.html, pcb_check_console.txt
echo.
pause
exit /b 0

:nochecker
echo PCB-Checker was not found in ..\PCB-Checker - only the DRC was run.> out\pcb_check_console.txt
type out\pcb_check_console.txt
pause
exit /b 1

:nopcb
echo %PCB% was not found next to this file.
pause
exit /b 1

:nokicad
echo KiCad 8, 9 or 10 was not found in "C:\Program Files\KiCad".
echo Edit the KICAD line at the top of this file.
pause
exit /b 1
