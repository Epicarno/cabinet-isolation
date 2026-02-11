#!/usr/bin/env python3
"""
classify_datapoints.py — Определение DPT-классов точек данных по CSV-файлам.

Собирает все CSV-файлы из LCSMnemo/*, строит маппинг dpName → DPT-класс,
затем сопоставляет с извлечёнными точками из reports/datapoints/_all.txt.

Выход (reports/datapoints/):
  _classes.txt         — полный список: DP | КЛАСС | ОПИСАНИЕ
  _classes_unique.txt  — уникальные классы + количество точек в каждом
  _unmatched.txt       — точки, для которых класс не найден в CSV

Использование:
  python classify_datapoints.py
  python classify_datapoints.py SHD_12       # только один шкаф
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
SCRIPT_DIR  = Path(__file__).resolve().parent
MODULES_DIR = SCRIPT_DIR.parent
MNEMO_DIR   = MODULES_DIR / "ventcontent" / "panels" / "vision" / "LCSMnemo"
REPORT_DIR  = MODULES_DIR / "reports" / "datapoints"
ALL_DP_FILE = REPORT_DIR / "_all.txt"


def load_csv_mapping(mnemo_dir: Path,
                     cabinets: list[str] | None = None
                     ) -> dict[str, tuple[str, str]]:
    """Собираем dpName → (DPT-класс, описание) из всех CSV.

    При конфликте (одна точка в разных CSV с разным классом)
    берём последний встреченный — CSV ближайший к мнемосхеме.
    """
    mapping: dict[str, tuple[str, str]] = {}

    for cab_dir in sorted(mnemo_dir.iterdir()):
        if not cab_dir.is_dir():
            continue
        if cabinets and cab_dir.name not in cabinets:
            continue

        for csv_file in sorted(cab_dir.glob("*.csv")):
            try:
                text = csv_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for line in text.strip().split("\n")[1:]:   # skip header
                parts = line.split(",")
                if len(parts) < 5:
                    continue

                ref_name = parts[0].strip()
                dp_name  = parts[1].strip()
                dpt_cls  = parts[4].strip()
                desc     = parts[5].strip() if len(parts) > 5 else ""

                if dpt_cls:
                    # Индексируем по обоим ключам: refName (как в XML)
                    # и dpName (фактическое имя DP). Для 98 % строк
                    # они совпадают, но в ~13 случаях refName содержит
                    # суффикс (_1, _2), которого нет в dpName.
                    if ref_name:
                        mapping[ref_name] = (dpt_cls, desc)
                    if dp_name and dp_name != ref_name:
                        mapping[dp_name] = (dpt_cls, desc)

    return mapping


def load_datapoints(dp_file: Path) -> list[str]:
    """Загружаем список точек из _all.txt (или per-cabinet .txt)."""
    dps: list[str] = []
    for line in dp_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        dps.append(line)
    return dps


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Определение DPT-классов точек данных по CSV"
    )
    parser.add_argument(
        "cabinets", nargs="*",
        help="Шкафы для обработки (по умолчанию — все)"
    )
    parser.add_argument(
        "--dp-file", type=Path, default=ALL_DP_FILE,
        help="Файл со списком точек (по умолчанию _all.txt)"
    )
    args = parser.parse_args()

    cabinets = args.cabinets if args.cabinets else None

    if not MNEMO_DIR.is_dir():
        print(f"ОШИБКА: не найдена папка {MNEMO_DIR}", file=sys.stderr)
        sys.exit(1)

    # 1. Собираем маппинг из CSV
    print("Сбор CSV-маппинга из LCSMnemo/ ...")
    csv_map = load_csv_mapping(MNEMO_DIR, cabinets)
    print(f"  Точек в CSV: {len(csv_map)}")

    # 2. Загружаем список точек
    dp_file = args.dp_file
    if not dp_file.exists():
        print(f"ОШИБКА: не найден {dp_file}", file=sys.stderr)
        print("Сначала запустите extract_datapoints.py", file=sys.stderr)
        sys.exit(1)

    datapoints = load_datapoints(dp_file)
    print(f"  Точек в {dp_file.name}: {len(datapoints)}")

    # 3. Классифицируем
    classified: list[tuple[str, str, str]] = []   # (dp, class, desc)
    unmatched: list[str] = []
    class_counts: dict[str, int] = defaultdict(int)

    for dp in datapoints:
        if dp in csv_map:
            cls, desc = csv_map[dp]
            classified.append((dp, cls, desc))
            class_counts[cls] += 1
        else:
            unmatched.append(dp)

    # 4. Отчёты
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # — Полный список: DP | КЛАСС | ОПИСАНИЕ
    classes_file = REPORT_DIR / "_classes.txt"
    with open(classes_file, "w", encoding="utf-8") as f:
        f.write(f"# Классификация точек — {len(classified)} найдено, "
                f"{len(unmatched)} без класса\n")
        f.write(f"# {'DP':<60s} {'КЛАСС':<25s} ОПИСАНИЕ\n")
        f.write(f"# {'-'*58} {'-'*23} {'-'*30}\n")
        for dp, cls, desc in sorted(classified):
            f.write(f"{dp:<60s} {cls:<25s} {desc}\n")

    # — Уникальные классы
    unique_file = REPORT_DIR / "_classes_unique.txt"
    with open(unique_file, "w", encoding="utf-8") as f:
        f.write(f"# Уникальные DPT-классы — {len(class_counts)} классов\n\n")
        for cls in sorted(class_counts, key=lambda c: (-class_counts[c], c)):
            f.write(f"{cls:<30s} {class_counts[cls]:>5d} точек\n")

    # — Без класса
    unmatched_file = REPORT_DIR / "_unmatched.txt"
    with open(unmatched_file, "w", encoding="utf-8") as f:
        f.write(f"# Точки без класса в CSV — {len(unmatched)}\n")
        for dp in sorted(unmatched):
            f.write(f"{dp}\n")

    # Вывод на экран
    print(f"\n{'='*60}")
    print(f"Классифицировано: {len(classified)} / {len(datapoints)}")
    print(f"Без класса:       {len(unmatched)}")
    print(f"Уникальных классов: {len(class_counts)}")
    print(f"{'='*60}")

    print(f"\nКлассы (по убыванию):")
    for cls in sorted(class_counts, key=lambda c: (-class_counts[c], c)):
        print(f"  {cls:<30s} {class_counts[cls]:>5d}")

    if unmatched:
        print(f"\nБез класса (первые 10):")
        for dp in sorted(unmatched)[:10]:
            print(f"  {dp}")
        if len(unmatched) > 10:
            print(f"  ... ещё {len(unmatched) - 10}")

    print(f"\nОтчёты:")
    print(f"  {classes_file}")
    print(f"  {unique_file}")
    print(f"  {unmatched_file}")


if __name__ == "__main__":
    main()
