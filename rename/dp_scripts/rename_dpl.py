#!/usr/bin/env python3
"""
rename_dpl.py — Переименование точек данных в DPL-файлах по стандарту KKS.

Переименовывает DP-имена во ВСЕХ секциях DPL:
  # Datapoint/DpId, # Aliases/Comments, # DpValue, # AlertValue,
  # DistributionInfo, # DpFunction, # DpConvRawToIngMain,
  # DpConvIngToRawMain, # PeriphAddrMain, # DbArchiveInfo, # CNS

Использует тот же Excel-файл и правила, что и rename_kks.py.

Режимы:
  --dry-run  (по умолчанию) — только отчёт
  --apply    — записать изменения (оригиналы бэкапятся в DPLs/<ШКАФ>/backup/)

Использование:
  python dp_scripts/rename_dpl.py                   # dry-run все шкафы
  python dp_scripts/rename_dpl.py --apply            # применить
  python dp_scripts/rename_dpl.py SHD_03_1           # только один шкаф
  python dp_scripts/rename_dpl.py --apply SHD_03_1
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Windows cp1251 → UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ---------------------------------------------------------------------------
# Пути
# ---------------------------------------------------------------------------
SCRIPT_DIR  = Path(__file__).resolve().parent       # rename/dp_scripts/
SCRIPTS_DIR = SCRIPT_DIR.parent                      # rename/
MODULES_DIR = SCRIPTS_DIR.parent.parent              # Modules/
DPL_DIR     = MODULES_DIR / "DPLs"
REPORT_DIR  = MODULES_DIR / "reports"

# Подключаем rename_kks.py из родительской папки
sys.path.insert(0, str(SCRIPTS_DIR))
from rename_kks import (
    load_excel, transform_dp, extract_cabinet,
    EXCEL_FILE,
)


# ---------------------------------------------------------------------------
# Regex для DP-имён в DPL
# ---------------------------------------------------------------------------
# DP формат: Cabinet>System>Type>Point  или  Cabinet>System>Type>Point.element.sub
# Также плоские: SHUOD_03_1_StSign_3  или  SHUOD_03_1_StSign_3.State.P
#
# В DPL точка (DP) может встречаться как:
#   1) Начало строки (Datapoint/DpId, Aliases):  SHD_03_1>P3_V3>DI>KZ1\tTAIRA_DI\t...
#   2) После пробела/таба (DpValue, AlertValue и др.):  UI (2)/0\tSHD_03_1>UURV>AI>FE1.Value\t...
#   3) В CNS поле data:  720896 SHD_03_1>A1-A16>ZD>K1_12.state.emergency\t2
#
# Стратегия: line-by-line, ищем все вхождения DP с помощью regex,
# определяем — нужно ли переименовать базовую часть (до первой точки).

# Паттерн для DP с элементами (через ">"):
#   SHD_03_1>UURV>AI>FE1.Value  или  SHD_03_1>UURV>AI>FE1
_DP_WITH_GT = re.compile(
    r'(?<![A-Za-z0-9_>.])'                         # не часть другого слова
    r'([A-Za-z][A-Za-z0-9_]*(?:>[A-Za-z0-9_\-]+)+)' # SHD_03_1>...>Point
    r'(\.[A-Za-z0-9_.]*)?'                           # .element.sub (опционально)
    r'(?![A-Za-z0-9_>])'                             # не продолжается
)

# Паттерн для физических точек (без ">"):
#   SHUOD_03_1_StSign_3  или  SHUOD_03_1_StSign_3.State.P
_DP_PHYS = re.compile(
    r'(?<![A-Za-z0-9_.])'
    r'([A-Za-z][A-Za-z0-9_]*_(?:StSign|OIP)_\d+)'
    r'(\.[A-Za-z0-9_.]*)?'
    r'(?![A-Za-z0-9_])'
)


def rename_line(line: str,
                cab_to_block: dict[str, str],
                explicit_map: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    """Переименовывает все DP-имена в одной строке.

    Returns:
        (new_line, [(old_dp_base, new_dp_base), ...])
    """
    changes: list[tuple[str, str]] = []

    def replacer_gt(m: re.Match) -> str:
        base = m.group(1)           # SHD_03_1>UURV>AI>FE1
        suffix = m.group(2) or ""   # .Value  или  ""
        new_base = transform_dp(base, cab_to_block, explicit_map)
        if new_base is None:
            return m.group(0)
        changes.append((base, new_base))
        return new_base + suffix

    def replacer_phys(m: re.Match) -> str:
        base = m.group(1)           # SHUOD_03_1_StSign_3
        suffix = m.group(2) or ""   # .State.P  или  ""
        new_base = transform_dp(base, cab_to_block, explicit_map)
        if new_base is None:
            return m.group(0)
        changes.append((base, new_base))
        return new_base + suffix

    # Сначала обрабатываем DP с ">" (более специфичный), потом физические
    new_line = _DP_WITH_GT.sub(replacer_gt, line)
    new_line = _DP_PHYS.sub(replacer_phys, new_line)

    return new_line, changes


def process_dpl(dpl_path: Path,
                cab_to_block: dict[str, str],
                explicit_map: dict[str, str],
                apply: bool) -> list[tuple[int, str, str]]:
    """Обрабатывает один DPL-файл.

    Returns:
        [(line_no, old_dp, new_dp), ...]
    """
    try:
        text = dpl_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    lines = text.splitlines(keepends=True)
    all_changes: list[tuple[int, str, str]] = []
    modified = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Пропускаем заголовки секций и пустые строки
        if not stripped or stripped.startswith("#") or stripped.startswith("TypeName"):
            continue
        # Пропускаем секцию DpType (определения типов — DP-имён нет)
        # DpType строки имеют формат: "TAIRA_PUMP.TAIRA_PUMP\t1#1" или "\tState\t21#2"
        # Их отличает отсутствие ">" и то что первое поле = TypeName.TypeName
        # Мы безопасно можем их обработать — transform_dp вернёт None для них

        new_line, changes = rename_line(line, cab_to_block, explicit_map)
        if changes:
            lines[i] = new_line
            modified = True
            for old_dp, new_dp in changes:
                all_changes.append((i + 1, old_dp, new_dp))

    if modified and apply:
        # Бэкап
        backup_dir = dpl_path.parent / "backup"
        backup_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{dpl_path.stem}_{ts}{dpl_path.suffix}"
        backup_path = backup_dir / backup_name
        if not backup_path.exists():
            shutil.copy2(dpl_path, backup_path)

        dpl_path.write_text("".join(lines), encoding="utf-8", newline="")

    return all_changes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Переименование точек данных в DPL по стандарту KKS"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Реально записать изменения (по умолчанию — dry-run)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Только отчёт (по умолчанию)"
    )
    parser.add_argument(
        "cabinets", nargs="*",
        help="Шкафы для обработки (по умолчанию — все в DPLs/)"
    )
    args = parser.parse_args()

    if args.apply:
        args.dry_run = False

    if not EXCEL_FILE.exists():
        print(f"ОШИБКА: не найден файл {EXCEL_FILE}", file=sys.stderr)
        sys.exit(1)

    if not DPL_DIR.is_dir():
        print(f"ОШИБКА: папка {DPL_DIR} не найдена", file=sys.stderr)
        sys.exit(1)

    # Загружаем правила
    print(f"Загрузка правил из {EXCEL_FILE.name} ...")
    cab_to_block, explicit_map = load_excel(EXCEL_FILE)
    print(f"  Шкафов: {len(cab_to_block)}, явных маппингов: {len(explicit_map)}")

    # Определяем шкафы
    if args.cabinets:
        cab_dirs = [DPL_DIR / c for c in args.cabinets if (DPL_DIR / c).is_dir()]
    else:
        cab_dirs = sorted(d for d in DPL_DIR.iterdir() if d.is_dir())

    if not cab_dirs:
        print("Нет папок шкафов в DPLs/.")
        return

    mode_label = "APPLY" if args.apply else "DRY-RUN"
    print(f"\nРежим: {mode_label}")
    print(f"Шкафы: {', '.join(d.name for d in cab_dirs)}\n")

    grand_total = 0
    grand_files = 0
    all_report: list[tuple[str, str, int, str, str]] = []  # (cab, file, line, old, new)

    for cab_dir in cab_dirs:
        cab_name = cab_dir.name
        dpl_files = sorted(cab_dir.glob("*.dpl"))
        if not dpl_files:
            print(f"  [{cab_name}] нет DPL файлов")
            continue

        cab_changes = 0
        cab_files = 0

        for dpl_file in dpl_files:
            changes = process_dpl(dpl_file, cab_to_block, explicit_map, apply=args.apply)
            if changes:
                cab_files += 1
                cab_changes += len(changes)
                for line_no, old, new in changes:
                    all_report.append((cab_name, dpl_file.name, line_no, old, new))
                print(f"  [{cab_name}] {dpl_file.name}: {len(changes)} замен")
            else:
                print(f"  [{cab_name}] {dpl_file.name}: без изменений")

        grand_total += cab_changes
        grand_files += cab_files

    # Статистика
    print(f"\n{'='*60}")
    print(f"Итого: {grand_total} замен в {grand_files} файлах")
    print(f"{'='*60}")

    # Группируем по типу замены
    change_types: dict[str, int] = defaultdict(int)
    for _, _, _, old, new in all_report:
        if ">" not in old and ("StSign" in old or "OIP" in old):
            change_types["PHYSICAL (StSign/OIP)"] += 1
        elif ">" not in old:
            change_types["FLAT (без >)"] += 1
        elif new.count(">") == old.count(">") + 1:
            first_seg = new.split(">")[0]
            rest = ">".join(new.split(">")[1:])
            if rest == old:
                change_types["PREFIX (добавлен блок)"] += 1
            else:
                change_types["RESTRUCTURED"] += 1
        else:
            change_types["RESTRUCTURED"] += 1

    if change_types:
        print("\nТипы замен:")
        for ctype, count in sorted(change_types.items(), key=lambda x: -x[1]):
            print(f"  {count:5d}  {ctype}")

    # Отчёт
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / "kks_rename_dpl.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"KKS DPL Rename Report ({mode_label})\n")
        f.write(f"{'='*60}\n")
        f.write(f"Замен: {grand_total}, файлов: {grand_files}\n\n")

        by_file: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
        for cab, fname, line_no, old, new in all_report:
            key = f"{cab}/{fname}"
            by_file[key].append((line_no, old, new))

        for key in sorted(by_file):
            f.write(f"\n--- {key} ---\n")
            for line_no, old, new in by_file[key]:
                f.write(f"  L{line_no}: {old}\n")
                f.write(f"       => {new}\n")

    print(f"\nОтчёт: {report_file}")

    # Примеры
    if all_report:
        print(f"\nПримеры замен (первые 10):")
        for cab, fname, line_no, old, new in all_report[:10]:
            print(f"  {cab}/{fname}:L{line_no}")
            print(f"    {old}  =>  {new}")


if __name__ == "__main__":
    main()
