"""
Pipeline-раннер для изоляции шкафов (замена run_pipeline.bat).

Запуск:
  python run_pipeline.py                  — полный прогон
  python run_pipeline.py --append         — append-режим отчётов
  python run_pipeline.py --from 5         — начать с шага 5
  python run_pipeline.py --only 8         — только шаг 8

Шаги:
   1. process_mnemo.py           — копирование объектов, подстановка путей
   2. fix_cross_refs.py          — исправление перекрёстных ссылок
   3. cleanup_orphans.py 2       — удаление лишних файлов
   4. clean_commented_refs.py    — очистка закомментированных ссылок (--apply)
   5. validate_refs.py           — валидация ссылок
   6. split_ctl.py               — разбиение PNR_Ventcontent.ctl
   7. replace_scripts.py         — замена #uses в объектах
   8. scan_problems.py           — анализ: проблемные комментарии
   9. check_other_scripts.py     — анализ: чужие скрипты (→ JSON)
  10. cleanup_classes.py         — удаление лишних if-блоков (по JSON)
  11. collect_output.py          — сборка output/
"""

import os
import sys
import subprocess
import argparse
import time

# UTF-8 для вывода (Windows cp866/cp1251 ломает Unicode-символы)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    (1,  "process_mnemo.py",           ["python", "process_mnemo.py"]),
    (2,  "fix_cross_refs.py",          ["python", "fix_cross_refs.py"]),
    (3,  "cleanup_orphans.py (mode 2)",["python", "cleanup_orphans.py", "2"]),
    (4,  "clean_commented_refs.py",    ["python", "clean_commented_refs.py", "--apply"]),
    (5,  "validate_refs.py",           ["python", "validate_refs.py"]),
    (6,  "split_ctl.py",              ["python", "split_ctl.py"]),
    (7,  "replace_scripts.py",         ["python", "replace_scripts.py"]),
    (8,  "scan_problems.py (analysis)",["python", "scan_problems.py"]),
    (9,  "check_other_scripts.py (→ JSON)", ["python", "check_other_scripts.py"]),
    (10, "cleanup_classes.py (uses JSON)",  ["python", "cleanup_classes.py"]),
    (11, "collect_output.py (deploy)", ["python", "collect_output.py", "--clean"]),
]

TOTAL = len(STEPS)


def run_step(num: int, name: str, cmd: list[str], append: bool) -> bool:
    """Выполняет один шаг. Возвращает True при успехе."""
    # Шаги с поддержкой --append
    APPEND_STEPS = {1, 2, 3, 4, 5, 7, 8, 9, 10}

    full_cmd = list(cmd)
    if append and num in APPEND_STEPS:
        full_cmd.append("--append")

    print()
    print("─" * 56)
    print(f"  [{num}/{TOTAL}]  {name}")
    print("─" * 56)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    t0 = time.time()
    result = subprocess.run(
        full_cmd,
        cwd=SCRIPTS_DIR,
        env=env,
    )
    elapsed = time.time() - t0

    if result.returncode == 0:
        print(f"  [{num}/{TOTAL}]  OK  ({elapsed:.1f}s)")
        return True
    else:
        print(f"  [{num}/{TOTAL}]  FAILED  (rc={result.returncode}, {elapsed:.1f}s)")
        return False


def main():
    parser = argparse.ArgumentParser(description="Ventcontent Split Pipeline")
    parser.add_argument("--append", action="store_true",
                        help="Append-режим для отчётов")
    parser.add_argument("--from", type=int, default=1, dest="from_step",
                        help="Начать с шага N")
    parser.add_argument("--only", type=int, default=0,
                        help="Выполнить только шаг N")
    args = parser.parse_args()

    print()
    print("═" * 56)
    print("  Ventcontent Split Pipeline")
    print("═" * 56)
    print()
    if args.append:
        print("  Отчёты: append")
    else:
        print("  Отчёты: overwrite")
    if args.from_step > 1:
        print(f"  Начать с шага: {args.from_step}")
    if args.only:
        print(f"  Только шаг: {args.only}")
    print(f"  Каталог: {SCRIPTS_DIR}")

    passed = 0
    failed = 0
    skipped = 0

    for num, name, cmd in STEPS:
        # --only: выполнить только указанный шаг
        if args.only and args.only != num:
            continue

        # --from: пропустить шаги до указанного
        if not args.only and num < args.from_step:
            print(f"  [{num}/{TOTAL}]  SKIP  {name}")
            skipped += 1
            continue

        ok = run_step(num, name, cmd, args.append)
        if ok:
            passed += 1
        else:
            failed += 1
            if args.only:
                break
            print()
            print(f"  Pipeline остановлен. Продолжить:")
            hint = f"  python run_pipeline.py"
            if args.append:
                hint += " --append"
            hint += f" --from {num}"
            print(hint)
            break

    print()
    print("═" * 56)
    if failed:
        print("  РЕЗУЛЬТАТ: ОШИБКА")
    else:
        print("  РЕЗУЛЬТАТ: OK")
    print(f"  Выполнено: {passed}  Ошибок: {failed}  Пропущено: {skipped}")
    print("═" * 56)
    print()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
