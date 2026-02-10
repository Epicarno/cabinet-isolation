@echo off
setlocal EnableDelayedExpansion

REM  Ventcontent Split Pipeline
REM
REM  run_pipeline.bat                    - full run
REM  run_pipeline.bat --append           - append reports
REM  run_pipeline.bat --from 5           - start from step 5
REM  run_pipeline.bat --only 8           - only step 8

cd /d "%~dp0"

set "APPEND_FLAG="
set "FROM_STEP=1"
set "ONLY_STEP=0"
set "PASS=0"
set "FAIL=0"
set "SKIP=0"

:parse_args
if "%~1"=="" goto args_done
if "%~1"=="--append" (set "APPEND_FLAG=--append"& shift & goto parse_args)
if "%~1"=="--from"   (set "FROM_STEP=%~2"& shift & shift & goto parse_args)
if "%~1"=="--only"   (set "ONLY_STEP=%~2"& shift & shift & goto parse_args)
echo Unknown argument: %~1
exit /b 1
:args_done

echo.
echo ========================================================
echo   Ventcontent Split Pipeline
echo ========================================================
echo.
if defined APPEND_FLAG (echo   Reports: append mode) else (echo   Reports: overwrite)
if !FROM_STEP! GTR 1 echo   Start from step: !FROM_STEP!
if !ONLY_STEP! NEQ 0 echo   Only step: !ONLY_STEP!
echo   Directory: %cd%
echo.

call :run_step 1 "process_mnemo.py" "python process_mnemo.py !APPEND_FLAG!"
if !FAIL! GTR 0 goto :done

call :run_step 2 "fix_cross_refs.py" "python fix_cross_refs.py !APPEND_FLAG!"
if !FAIL! GTR 0 goto :done

call :run_step 3 "cleanup_orphans.py (mode 2)" "python cleanup_orphans.py 2 !APPEND_FLAG!"
if !FAIL! GTR 0 goto :done

call :run_step 4 "validate_refs.py" "python validate_refs.py !APPEND_FLAG!"
if !FAIL! GTR 0 goto :done

call :run_step 5 "split_ctl.py" "python split_ctl.py !APPEND_FLAG!"
if !FAIL! GTR 0 goto :done

call :run_step 6 "replace_scripts.py" "python replace_scripts.py !APPEND_FLAG!"
if !FAIL! GTR 0 goto :done

call :run_step 7 "scan_problems.py (analysis)" "python scan_problems.py !APPEND_FLAG!"
if !FAIL! GTR 0 goto :done

call :run_step 8 "check_other_scripts.py (analysis -> JSON)" "python check_other_scripts.py !APPEND_FLAG!"
if !FAIL! GTR 0 goto :done

call :run_step 9 "cleanup_classes.py (uses JSON)" "python cleanup_classes.py !APPEND_FLAG!"

:done
echo.
echo ========================================================
if !FAIL! GTR 0 (
    echo   RESULT: FAILED
) else (
    echo   RESULT: OK
)
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
    echo [!S_NUM!/9] SKIP !S_NAME!
    set /a "SKIP+=1"
    goto :eof
)

echo.
echo --------------------------------------------------------
echo [!S_NUM!/9] !S_NAME!
echo --------------------------------------------------------

!S_CMD!

if !ERRORLEVEL! EQU 0 (
    echo [!S_NUM!/9] OK
    set /a "PASS+=1"
) else (
    echo [!S_NUM!/9] FAILED
    echo Pipeline stopped. To continue: run_pipeline.bat !APPEND_FLAG! --from !S_NUM!
    set /a "FAIL+=1"
)
goto :eof
