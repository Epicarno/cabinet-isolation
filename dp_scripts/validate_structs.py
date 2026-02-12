#!/usr/bin/env python3
"""
validate_structs.py — Валидация DPT-классов: CSV struct ↔ DPL DpType.

Сравнивает struct-значения из CSV-файлов мнемосхем (колонка 5)
с DpType-определениями из DPL-файлов в DPLs/<ШКАФ>/.

Категории расхождений:
  ERROR   — struct в CSV, которого нет в DPL (вероятная ошибка)
  WARN    — _Static-вариант существующего DPL-типа (без DPT-определения)
  INFO    — специфичный класс (SCADTECH, DI_scadtech и т.п.) — оставлен
  UNUSED  — DPL-тип без ссылок в CSV (может быть лишним в DPL)

Выход (reports/datapoints/):
  _validate_structs.txt  — полный отчёт
  _struct_errors.txt     — только ошибки, требующие исправления

Использование:
  python validate_structs.py                  # все шкафы из cabinets.txt
  python validate_structs.py SHD_03_1         # один шкаф
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Windows cp1251 ломает Unicode-символы → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from collections import defaultdict

# ---------------------------------------------------------------------------
SCRIPT_DIR  = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent          # scripts/
MODULES_DIR = SCRIPTS_DIR.parent          # Modules/
MNEMO_DIR   = MODULES_DIR / "ventcontent" / "panels" / "vision" / "LCSMnemo"
DPL_DIR     = MODULES_DIR / "DPLs"
REPORT_DIR  = MODULES_DIR / "reports" / "datapoints"

# Специфичные классы — не трогаем, помечаем как INFO
KNOWN_SPECIFIC = {
    "SCADTECH_DI_SHUOD",
    "DI_scadtech",
    "DI_scadtech_PNR",
    "SCADTECH_DI",
    "SCADTECH_AI",
    "TAIRA_1_DI_VENT",
}

# Известные ошибки именования: CSV struct → правильное имя DPL
KNOWN_RENAMES = {
    "PUMP_ETRA": "ETRA_PUMP",
}


def parse_dpl_types(dpl_path: Path) -> set[str]:
    """Извлекает имена DpType из DPL-файла.

    Формат секции # DpType:
      TypeName                          ← заголовок (пропускаем)
      TAIRA_PUMP.TAIRA_PUMP\t1#1        ← корневой тип (берём часть до точки)
      \tState\t21#2                     ← вложенный элемент (пропускаем)
      \tname\t25#4
      TAIRA_AI.TAIRA_AI\t1#1            ← следующий тип
    """
    types: set[str] = set()
    in_dptype_section = False

    try:
        text = dpl_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return types

    for line in text.splitlines():
        stripped = line.strip()

        if stripped == "# DpType":
            in_dptype_section = True
            continue
        if stripped.startswith("# ") and in_dptype_section:
            if stripped != "# DpType":
                in_dptype_section = False
                continue

        if not in_dptype_section or not stripped:
            continue

        # Пропускаем вложенные элементы (начинаются с tab)
        if line.startswith("\t"):
            continue

        # Пропускаем заголовок "TypeName"
        if stripped == "TypeName":
            continue

        # Корневой DpType: "TAIRA_PUMP.TAIRA_PUMP\t1#1"
        # Формат: DPT_NAME.DPT_NAME\t<type_id>#<element_id>
        parts = stripped.split("\t")
        if len(parts) >= 2 and "." in parts[0]:
            type_name = parts[0].split(".")[0]
            types.add(type_name)

    return types


def parse_dpl_instances(dpl_path: Path) -> dict[str, str]:
    """Извлекает DP-инстансы из DPL-файла.

    Формат секции # Datapoint/DpId:
      dpName\t\tID  (dpName — имя точки, ID — числовой)

    Возвращает dict: dpName → dpType (из предыдущей строки типа).
    """
    instances: dict[str, str] = {}
    in_dp_section = False
    current_type = ""

    try:
        text = dpl_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return instances

    for line in text.splitlines():
        stripped = line.strip()

        if stripped == "# Datapoint/DpId":
            in_dp_section = True
            continue
        if stripped.startswith("# ") and in_dp_section:
            if stripped != "# Datapoint/DpId":
                in_dp_section = False
                continue

        if not in_dp_section:
            continue

        if not stripped:
            continue

        parts = stripped.split("\t")

        # Строка типа: "TypeName\tTypeId"
        if len(parts) == 2 and parts[1].isdigit():
            current_type = parts[0]
            continue

        # Строка инстанса: "dpName\t\tDPID" (второе поле пустое)
        if len(parts) >= 3 and parts[1] == "" and current_type:
            dp_name = parts[0]
            if dp_name and not dp_name.startswith("_"):
                instances[dp_name] = current_type

    return instances


def load_csv_structs(mnemo_dir: Path,
                     cabinet: str) -> dict[str, list[tuple[str, str]]]:
    """Собирает struct-значения из CSV: struct → [(refName, csv_file), ...].

    Фильтрует по принадлежности к шкафу.
    """
    structs: dict[str, list[tuple[str, str]]] = defaultdict(list)

    cab_dir = mnemo_dir / cabinet
    if not cab_dir.is_dir():
        return structs

    for csv_file in sorted(cab_dir.glob("*.csv")):
        try:
            text = csv_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for line in text.strip().split("\n")[1:]:  # skip header
            parts = line.split(",")
            if len(parts) < 5:
                continue

            ref_name = parts[0].strip()
            dp_name  = parts[1].strip()
            struct   = parts[4].strip()

            if not struct:
                continue

            # Точка должна принадлежать шкафу
            ref_ok = ref_name.startswith(cabinet)
            dp_ok  = dp_name.startswith(cabinet)
            if not ref_ok and not dp_ok:
                continue

            key = dp_name if dp_name else ref_name
            structs[struct].append((key, csv_file.name))

    return structs


def classify_mismatch(struct: str, dpl_types: set[str]) -> tuple[str, str]:
    """Определяет категорию расхождения для struct без DPL-типа.

    Возвращает (категория, пояснение).
    """
    # Известная ошибка именования
    if struct in KNOWN_RENAMES:
        correct = KNOWN_RENAMES[struct]
        return ("ERROR", f"перевёрнутое имя → правильно: {correct}")

    # Специфичный класс — не трогаем
    if struct in KNOWN_SPECIFIC:
        return ("INFO", "специфичный класс — оставлен")

    # Начинается с известного специфичного префикса
    for prefix in ("SCADTECH_", "DI_scadtech"):
        if struct.startswith(prefix):
            return ("INFO", "специфичный класс — оставлен")

    # _Static — суффикс, базовый тип может быть в DPL
    if struct.endswith("_Static"):
        base = struct.replace("_Static", "")
        # Исправляем VZZDR → VZZD
        base_norm = base.replace("VZZDR", "VZZD")
        if base in dpl_types or base_norm in dpl_types:
            return ("WARN", f"Static-вариант типа {base_norm} (DPT без определения)")
        return ("WARN", f"Static-вариант, базовый тип {base} тоже не найден в DPL")

    # Неизвестный тип
    return ("ERROR", "struct не найден в DPL")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Валидация DPT-классов: CSV struct ↔ DPL DpType"
    )
    parser.add_argument(
        "cabinets", nargs="*",
        help="Шкафы для обработки (по умолчанию — из cabinets.txt)"
    )
    args = parser.parse_args()

    # Определяем шкафы
    if args.cabinets:
        cabinets = args.cabinets
    else:
        cabinets_file = SCRIPTS_DIR / "cabinets.txt"
        if cabinets_file.exists():
            cabinets = [
                line.strip()
                for line in cabinets_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        else:
            # Все папки в DPLs/
            if DPL_DIR.exists():
                cabinets = sorted(d.name for d in DPL_DIR.iterdir() if d.is_dir())
            else:
                print(f"ОШИБКА: не найдена папка {DPL_DIR}", file=sys.stderr)
                sys.exit(1)

    if not cabinets:
        print("Нет шкафов для обработки", file=sys.stderr)
        sys.exit(1)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    all_report_lines: list[str] = []
    all_errors: list[str] = []
    total_ok = 0
    total_warn = 0
    total_error = 0
    total_info = 0
    total_unused = 0

    for cabinet in cabinets:
        print(f"\n{'='*60}")
        print(f"Шкаф: {cabinet}")
        print(f"{'='*60}")

        # 1. Собираем DPT-типы из DPL
        dpl_cab_dir = DPL_DIR / cabinet
        dpl_types: set[str] = set()
        if dpl_cab_dir.is_dir():
            for dpl_file in sorted(dpl_cab_dir.glob("*.dpl")):
                types = parse_dpl_types(dpl_file)
                dpl_types.update(types)
                print(f"  DPL: {dpl_file.name} → {len(types)} типов")
        else:
            print(f"  ⚠ DPL-папка не найдена: {dpl_cab_dir}")

        # 2. Собираем struct-значения из CSV
        csv_structs = load_csv_structs(MNEMO_DIR, cabinet)
        print(f"  CSV: {len(csv_structs)} уникальных struct-значений")

        if not csv_structs:
            print("  Нет CSV-данных для анализа")
            continue

        # 3. Сравниваем
        ok_structs: list[str] = []
        issues: list[tuple[str, str, str, int]] = []  # (struct, cat, msg, count)

        for struct in sorted(csv_structs.keys()):
            count = len(csv_structs[struct])
            if struct in dpl_types:
                ok_structs.append(struct)
                total_ok += count
            else:
                cat, msg = classify_mismatch(struct, dpl_types)
                issues.append((struct, cat, msg, count))
                if cat == "ERROR":
                    total_error += count
                elif cat == "WARN":
                    total_warn += count
                else:
                    total_info += count

        # DPL-типы без ссылок в CSV
        csv_struct_names = set(csv_structs.keys())
        unused_types = sorted(dpl_types - csv_struct_names)
        total_unused += len(unused_types)

        # Формируем отчёт
        section = []
        section.append(f"\n{'='*60}")
        section.append(f"ШКАФ: {cabinet}")
        section.append(f"  DPL-типов: {len(dpl_types)}   CSV struct: {len(csv_structs)}")
        section.append(f"{'='*60}")

        if ok_structs:
            section.append(f"\n✅ СОВПАДАЮТ ({len(ok_structs)} типов):")
            for s in ok_structs:
                cnt = len(csv_structs[s])
                section.append(f"  {s:<35s} {cnt:>5d} точек")

        if issues:
            section.append(f"\n⚠ РАСХОЖДЕНИЯ ({len(issues)} типов):")
            for struct, cat, msg, count in issues:
                section.append(f"  [{cat:5s}] {struct:<35s} {count:>5d} точек — {msg}")

                # Для ошибок — детали по CSV-файлам
                if cat == "ERROR":
                    files = set(f for _, f in csv_structs[struct])
                    err_line = f"  {cabinet}: {struct} ({count} точек) — {msg}"
                    err_line += f"  [CSV: {', '.join(sorted(files))}]"
                    all_errors.append(err_line)

        if unused_types:
            section.append(f"\n🔇 DPL-ТИПЫ БЕЗ CSV ({len(unused_types)}):")
            for t in unused_types:
                section.append(f"  {t}")

        all_report_lines.extend(section)

        # Консольный вывод
        for line in section:
            print(line)

    # Сводка
    summary = []
    summary.append(f"\n{'='*60}")
    summary.append(f"ИТОГО")
    summary.append(f"{'='*60}")
    summary.append(f"  ✅ OK:        {total_ok:>6d} точек (struct совпадает с DPL)")
    summary.append(f"  ⚠  WARN:      {total_warn:>6d} точек (_Static без DPT)")
    summary.append(f"  ❌ ERROR:     {total_error:>6d} точек (struct ≠ DPL)")
    summary.append(f"  ℹ  INFO:      {total_info:>6d} точек (специфичные, оставлены)")
    summary.append(f"  🔇 UNUSED:    {total_unused:>6d} DPL-типов без CSV")

    all_report_lines.extend(summary)
    for line in summary:
        print(line)

    # Записываем отчёты
    report_file = REPORT_DIR / "_validate_structs.txt"
    report_file.write_text("\n".join(all_report_lines), encoding="utf-8")
    print(f"\nОтчёт: {report_file}")

    if all_errors:
        errors_file = REPORT_DIR / "_struct_errors.txt"
        header = [
            f"# Ошибки struct: CSV ≠ DPL — {len(all_errors)} записей",
            f"# Эти struct-значения нужно исправить в CSV-файлах\n",
        ]
        errors_file.write_text(
            "\n".join(header + all_errors), encoding="utf-8"
        )
        print(f"Ошибки: {errors_file}")
    else:
        print("Ошибок не найдено!")


if __name__ == "__main__":
    main()
