#!/usr/bin/env python3
"""
fix_dp_indices.py — Исправление индексов dpNameEdit после переименования KKS.

После переименования точек по стандарту KKS глубина пути увеличивается:
  До:   SHD_03_1>P1_V1>AI>T0       (3 сегмента + точка)
  После: B3>SHD_03_1>P1_V1>AI>T0    (4 сегмента + точка)

Скрипты объектов парсят путь через dpName.split(">") и обращаются к
сегментам по индексам [1], [2], [3]. После добавления блока все индексы
сдвигаются на +1. Этот скрипт находит и исправляет паттерны конкатенации:

  До:
    dpNameEdit[1] + ">" + dpNameEdit[2] + ">" + dpNameEdit[3] + ">" + "T1"
  После:
    dpNameEdit[1] + ">" + dpNameEdit[2] + ">" + dpNameEdit[3] + ">" + dpNameEdit[4] + ">" + "T1"

Обрабатываемые форматы кавычек в XML:
  - \\"SUFFIX\\"    (внутри CDATA/скриптов)
  - &quot;SUFFIX&quot;  (в атрибутах)

Режимы:
  --dry-run  (по умолчанию) — только отчёт
  --apply    — реально записать изменения

Использование:
  python fix_dp_indices.py                 # dry-run
  python fix_dp_indices.py --apply         # применить
  python fix_dp_indices.py SHD_03_1        # только шкаф
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR  = Path(__file__).resolve().parent
MODULES_DIR = SCRIPT_DIR.parent.parent    # Modules/
REPORT_DIR  = MODULES_DIR / "reports"

# ---------------------------------------------------------------------------
# Паттерн: dpNameEdit[1] + ">" + dpNameEdit[2] + ">" + dpNameEdit[3] + ">" + "SUFFIX"
# В XML кавычки экранируются как \" (обратный слэш + кавычка)
# ---------------------------------------------------------------------------
# Реальный формат в файле:
#   dpNameEdit[3] + \">\" + \"T1\"
# Нужно заменить на:
#   dpNameEdit[3] + \">\" + dpNameEdit[4] + \">\" + \"T1\"

# Паттерн для формата \"...\"  (\\\" в regex = литеральный \")
_PAT_BACKSLASH = re.compile(
    r'(dpNameEdit\[3\]'                         # dpNameEdit[3]
    r'\s*\+\s*'                                  # +
    r'\\">\\"\s*\+\s*'                           # \">\" +
    r')\\"'                                      # \"  (открытие суффикса)
    r'([A-Za-z0-9_]+)'                           # суффикс (T1, KZ1, ...)
    r'\\"'                                       # \"  (закрытие суффикса)
)

# Паттерн для формата &quot;...&quot;
# В XML символ > кодируется как &gt;, поэтому разделитель: &quot;&gt;&quot;
_PAT_AMPQUOT = re.compile(
    r'(dpNameEdit\[3\]'
    r'\s*\+\s*'
    r'&quot;&gt;&quot;\s*\+\s*'
    r')&quot;'
    r'([A-Za-z0-9_]+)'
    r'&quot;'
)


def fix_content(content: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Исправляем все паттерны dpNameEdit[3]+">"+SUFFIX → dpNameEdit[3]+">"+dpNameEdit[4]+">"+SUFFIX.

    Returns:
        (new_content, list of (line_number, old_fragment, new_fragment))
    """
    changes: list[tuple[int, str, str]] = []

    def replacer_backslash(m: re.Match) -> str:
        prefix = m.group(1)   # dpNameEdit[3] + \">\" +
        suffix = m.group(2)   # T1
        old_frag = m.group(0)
        new_frag = f'{prefix}dpNameEdit[4] + \\">\\\" + \\"{suffix}\\"'
        line_no = content[:m.start()].count('\n') + 1
        changes.append((line_no, suffix, old_frag))
        return new_frag

    def replacer_ampquot(m: re.Match) -> str:
        prefix = m.group(1)
        suffix = m.group(2)
        old_frag = m.group(0)
        new_frag = f'{prefix}dpNameEdit[4] + &quot;&gt;&quot; + &quot;{suffix}&quot;'
        line_no = content[:m.start()].count('\n') + 1
        changes.append((line_no, suffix, old_frag))
        return new_frag

    new_content = _PAT_BACKSLASH.sub(replacer_backslash, content)
    new_content = _PAT_AMPQUOT.sub(replacer_ampquot, new_content)

    return new_content, changes


def collect_files(cabinets_filter: list[str] | None) -> list[Path]:
    """Собираем XML-файлы из objects_*, output/, ventcontent/."""
    files: list[Path] = []

    # ventcontent/panels/objects/PV/ (оригиналы шаблонов)
    vent_obj = MODULES_DIR / "ventcontent" / "panels" / "objects"
    if vent_obj.is_dir():
        files.extend(sorted(vent_obj.rglob("*.xml")))

    # objects_* (изолированные копии)
    for obj_dir in sorted(MODULES_DIR.glob("objects_*")):
        if not obj_dir.is_dir():
            continue
        cab_name = obj_dir.name.removeprefix("objects_")
        if cabinets_filter and cab_name not in cabinets_filter:
            continue
        files.extend(sorted(obj_dir.rglob("*.xml")))

    # output/
    output_dir = MODULES_DIR / "output"
    if output_dir.is_dir():
        for cab_dir in sorted(output_dir.iterdir()):
            if not cab_dir.is_dir():
                continue
            if cabinets_filter and cab_dir.name not in cabinets_filter:
                continue
            files.extend(sorted(cab_dir.rglob("*.xml")))

    # _ventcontent/ (бэкап)
    backup_obj = MODULES_DIR / "_ventcontent" / "panels" / "objects"
    if backup_obj.is_dir():
        files.extend(sorted(backup_obj.rglob("*.xml")))

    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Исправление индексов dpNameEdit после KKS-переименования"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Реально записать изменения"
    )
    parser.add_argument(
        "cabinets", nargs="*",
        help="Шкафы для обработки (по умолчанию — все)"
    )
    args = parser.parse_args()

    cabinets_filter = args.cabinets if args.cabinets else None
    mode = "APPLY" if args.apply else "DRY-RUN"

    files = collect_files(cabinets_filter)
    print(f"Файлов для проверки: {len(files)}")
    print(f"Режим: {mode}\n")

    total_changes = 0
    files_changed = 0
    all_changes: list[tuple[Path, int, str, str]] = []

    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception:
            continue

        # Быстрая проверка — есть ли вообще dpNameEdit[3]
        if "dpNameEdit[3]" not in content:
            continue

        new_content, changes = fix_content(content)

        if changes:
            files_changed += 1
            total_changes += len(changes)
            try:
                rel = fpath.relative_to(MODULES_DIR)
            except ValueError:
                rel = fpath
            for line_no, suffix, old_frag in changes:
                all_changes.append((rel, line_no, suffix, old_frag))

            if args.apply:
                fpath.write_text(new_content, encoding="utf-8", newline="\n")

    # Результаты
    print(f"{'='*60}")
    print(f"Итого: {total_changes} исправлений в {files_changed} файлах")
    print(f"{'='*60}")

    # Группируем по суффиксу
    suffix_counts: dict[str, int] = defaultdict(int)
    for _, _, suffix, _ in all_changes:
        suffix_counts[suffix] += 1

    if suffix_counts:
        print("\nСуффиксы:")
        for suf, cnt in sorted(suffix_counts.items(), key=lambda x: -x[1]):
            print(f"  {cnt:5d}  {suf}")

    # Отчёт
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / "fix_dp_indices.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"fix_dp_indices Report ({mode})\n")
        f.write(f"{'='*60}\n")
        f.write(f"Исправлений: {total_changes}, файлов: {files_changed}\n\n")

        by_file: dict[Path, list[tuple[int, str]]] = defaultdict(list)
        for rel, line_no, suffix, _ in all_changes:
            by_file[rel].append((line_no, suffix))

        for rel in sorted(by_file):
            f.write(f"\n--- {rel} ---\n")
            for line_no, suffix in by_file[rel]:
                f.write(f"  L{line_no}: dpNameEdit[3]+>+\"{suffix}\" → dpNameEdit[3]+>+dpNameEdit[4]+>+\"{suffix}\"\n")

    print(f"\nОтчёт: {report_file}")

    if all_changes and not args.apply:
        print(f"\nПримеры (первые 5):")
        for rel, line_no, suffix, _ in all_changes[:5]:
            print(f"  {rel}:L{line_no}  суффикс \"{suffix}\"")
            print(f"    [3]+>+\"{suffix}\" → [3]+>+[4]+>+\"{suffix}\"")


if __name__ == "__main__":
    main()
