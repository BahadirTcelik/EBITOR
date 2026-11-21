@echo off
rem EE463 - KiCad checks of the generated schematic. Double-click this file.
rem Runs the ERC, exports the netlist and a PDF, and checks that every footprint exists in the KiCad library.
rem Results go to the "out" folder next to this file. Nothing in the project is modified.
setlocal EnableExtensions
cd /d "%~dp0"
set "KICAD="
if exist "C:\Program Files\KiCad\8.0\bin\kicad-cli.exe" set "KICAD=C:\Program Files\KiCad\8.0"
if exist "C:\Program Files\KiCad\9.0\bin\kicad-cli.exe" set "KICAD=C:\Program Files\KiCad\9.0"
if exist "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" set "KICAD=C:\Program Files\KiCad\10.0"
if not defined KICAD goto :nokicad
set "CLI=%KICAD%\bin\kicad-cli.exe"
if not exist out mkdir out
"%CLI%" version > out\kicad_version.txt 2>&1

echo [1/4] Electrical rules check ...
"%CLI%" sch erc --severity-all --units mm --format report --output out\erc.rpt ee463_dcdc.kicad_sch > out\erc_console.txt 2>&1
"%CLI%" sch erc --severity-all --units mm --format json --output out\erc.json ee463_dcdc.kicad_sch >> out\erc_console.txt 2>&1

echo [2/4] Netlist ...
"%CLI%" sch export netlist --format kicadsexpr --output out\ee463_dcdc.net ee463_dcdc.kicad_sch > out\netlist_console.txt 2>&1

echo [3/4] Schematic PDF ...
"%CLI%" sch export pdf --output out\ee463_dcdc_schematic.pdf ee463_dcdc.kicad_sch > out\pdf_console.txt 2>&1

echo [4/4] Footprint names ...
echo Footprints looked up in %KICAD%\share\kicad\footprints and in ee463.pretty> out\footprint_check.txt
for /f "usebackq tokens=1,* delims=:" %%A in ("footprints_used.txt") do call :chk "%%A" "%%B"

where python >nul 2>nul
if not errorlevel 1 python compare_netlist.py out\ee463_dcdc.net netlist\pins.csv > out\compare.txt 2>&1

echo.
echo Done. Results are in the "out" folder:
echo   erc.rpt, ee463_dcdc.net, ee463_dcdc_schematic.pdf, footprint_check.txt
echo.
pause
exit /b 0

:chk
set "FP=%KICAD%\share\kicad\footprints\%~1.pretty\%~2.kicad_mod"
if /i "%~1"=="ee463" set "FP=ee463.pretty\%~2.kicad_mod"
if exist "%FP%" (>>out\footprint_check.txt echo OK       %~1:%~2) else (>>out\footprint_check.txt echo MISSING  %~1:%~2)
goto :eof

:nokicad
echo KiCad 8, 9 or 10 was not found in "C:\Program Files\KiCad".
echo Edit the KICAD line at the top of this file.
pause
exit /b 1
