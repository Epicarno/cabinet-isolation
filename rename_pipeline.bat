@echo off
setlocal EnableDelayedExpansion

REM  KKS Rename Pipeline — Переименование точек данных
REM
REM  rename_pipeline.bat                    - полный прогон (dry-run)
REM  rename_pipeline.bat --apply            - применить изменения
REM  rename_pipeline.bat --from 3           - начать с шага 3
REM  rename_pipeline.bat --only 2           - только шаг 2
REM  rename_pipeline.bat --apply --from 3   - применить, начиная с шага 3
REM
REM  Шкафы читаются из cabinets.txt

cd /d "%~dp0"

set "APPLY_FLAG="
set "FROM_STEP=1"
set "ONLY_STEP=0"
set "PASS=0"
set "FAIL=0"
set "SKIP=0"

:parse_args
if "%~1"=="" goto args_done
if "%~1"=="--apply"  (set "APPLY_FLAG=--apply"& shift & goto parse_args)
if "%~1"=="--from"   (set "FROM_STEP=%~2"& shift & shift & goto parse_args)
if "%~1"=="--only"   (set "ONLY_STEP=%~2"& shift & shift & goto parse_args)
echo Unknown argument: %~1
exit /b 1
:args_done

if defined APPLY_FLAG (set "MODE=APPLY") else (set "MODE=DRY-RUN")

echo.
echo ========================================================
echo   KKS Rename Pipeline
echo ========================================================
echo.
echo   Mode: !MODE!
if !FROM_STEP! GTR 1 echo   Start from step: !FROM_STEP!
if !ONLY_STEP! NEQ 0 echo   Only step: !ONLY_STEP!
echo   Directory: %cd%
echo.

REM --- Шаг 1: Переименование точек в XML (мнемосхемы + объекты) ---
cd .
call :run_step 1 "rename_kks.py (XML)" "python rename_kks.py !APPLY_FLAG!"
if !FAIL! GTR 0 goto :done

REM --- Шаг 2: Переименование точек в CSV (мнемосхемы) ---
cd .
call :run_step 2 "rename_kks.py --csv (CSV)" "python rename_kks.py --csv !APPLY_FLAG!"
if !FAIL! GTR 0 goto :done

REM --- Шаг 3: Переименование точек в DPL ---
cd .
call :run_step 3 "dp_scripts/rename_dpl.py" "python dp_scripts/rename_dpl.py !APPLY_FLAG!"
if !FAIL! GTR 0 goto :done

REM --- Шаг 4: Валидация DPL после переименования ---
cd .
call :run_step 4 "dp_scripts/validate_dpl_points.py" "python dp_scripts/validate_dpl_points.py"
if !FAIL! GTR 0 goto :done

REM --- Шаг 5: Очистка DPL (CNS orphans + unused types) ---
cd .
call :run_step 5 "dp_scripts/clean_dpl.py" "python dp_scripts/clean_dpl.py --clean-cns-orphans --remove-unused-types !APPLY_FLAG!"
if !FAIL! GTR 0 goto :done

:done
echo.
echo ========================================================
if !FAIL! GTR 0 (
    echo   RESULT: FAILED
) else (
    echo   RESULT: OK
)
echo   Mode: !MODE!
echo   Pass: !PASS!  Fail: !FAIL!  Skip: !SKIP!
echo ========================================================
echo.

if !FAIL! GTR 0 exit /b 1
exit /b 0


:run_step
set "S_NUM=%~1"
set "S_NAME=%~2"
set "S_CMD=%~3"

if !ONLY_STEP! NEQ 0 if !ONLY_STEP! NEQ !S_NUM! goto :eof
if !ONLY_STEP! EQU 0 if !S_NUM! LSS !FROM_STEP! (
    echo [!S_NUM!/5] SKIP !S_NAME!
    set /a "SKIP+=1"
    goto :eof
)

echo.
echo --------------------------------------------------------
echo [!S_NUM!/5] !S_NAME!
echo --------------------------------------------------------

!S_CMD!
set "RC=!ERRORLEVEL!"

if !RC! EQU 0 (
    echo [!S_NUM!/5] OK
    set /a "PASS+=1"
) else (
    echo [!S_NUM!/5] FAILED
    echo Pipeline stopped. To continue: rename_pipeline.bat !APPLY_FLAG! --from !S_NUM!
    set /a "FAIL+=1"
)
goto :eof
