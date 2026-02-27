@echo off
REM  Ventcontent Split Pipeline (wrapper)
REM  Вся логика в run_pipeline.py — этот .bat просто вызывает его.
REM
REM  run_pipeline.bat                    - полный прогон
REM  run_pipeline.bat --append           - append-режим отчётов
REM  run_pipeline.bat --from 5           - начать с шага 5
REM  run_pipeline.bat --only 8           - только шаг 8

cd /d "%~dp0"
python run_pipeline.py %*
