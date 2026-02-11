"""
Извлечение всех уникальных точек данных (DP) из мнемосхем.

Формат точки в XML:  Name="ШКАФ>МНЕМО>ТИП>DP"
Например:            SHD_03_1>P4_V4>DI>KZ1

Результат:
  reports/datapoints/
    _all.txt                     ← все точки всех шкафов
    SHD_03_1.txt                 ← точки одного шкафа
    SHD_12.txt
    ...

Каждый файл содержит отсортированные уникальные точки, сгруппированные по мнемосхемам.

Использование:
  python extract_datapoints.py
"""

import re
from pathlib import Path
from collections import defaultdict
from parse_utils import read_text_safe, find_mnemo_dirs, SCRIPT_DIR, REPORT_DIR

OUTPUT_DIR = REPORT_DIR / "datapoints"

# Паттерн: Name="ШКАФ>МНЕМО>ТИП>DP"  (минимум 3 сегмента через >)
DP_PATTERN = re.compile(r'Name="([^"]*>[^"]*>[^"]*)"')


def extract_from_file(xml_path: Path) -> list[str]:
    """Извлекает все точки данных из одного XML."""
    text = read_text_safe(xml_path)
    if text is None:
        return []
    return DP_PATTERN.findall(text)


def main():
    mnemo_dirs = find_mnemo_dirs()
    if not mnemo_dirs:
        print("Папки шкафов не найдены (проверьте cabinets.txt)")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_points: list[str] = []
    total_cabinets = 0
    total_dps = 0

    print(f"Шкафов: {len(mnemo_dirs)}\n")

    for cab_dir in mnemo_dirs:
        cabinet = cab_dir.name
        # мнемосхема → список точек
        by_mnemo: dict[str, list[str]] = defaultdict(list)

        for xml_file in sorted(cab_dir.rglob("*.xml")):
            points = extract_from_file(xml_file)
            mnemo_name = xml_file.stem
            for p in points:
                by_mnemo[mnemo_name].append(p)

        if not by_mnemo:
            print(f"  [{cabinet}] нет точек")
            continue

        # Формируем файл шкафа
        lines: list[str] = []
        cab_unique: set[str] = set()

        for mnemo in sorted(by_mnemo.keys()):
            points = sorted(set(by_mnemo[mnemo]))
            lines.append(f"=== {mnemo} ({len(points)}) ===")
            for p in points:
                lines.append(f"  {p}")
                cab_unique.add(p)
            lines.append("")

        lines.insert(0, f"# {cabinet} — {len(cab_unique)} уникальных точек\n")

        # Записываем файл шкафа
        cab_file = OUTPUT_DIR / f"{cabinet}.txt"
        cab_file.write_text("\n".join(lines), encoding="utf-8")

        all_points.extend(cab_unique)
        total_cabinets += 1
        total_dps += len(cab_unique)

        print(f"  [{cabinet}] {len(cab_unique)} точек, {len(by_mnemo)} мнемосхем → {cab_file.name}")

    # Общий файл
    if all_points:
        all_unique = sorted(set(all_points))
        all_lines = [f"# Все точки — {len(all_unique)} уникальных\n"]
        all_lines.extend(all_unique)
        all_file = OUTPUT_DIR / "_all.txt"
        all_file.write_text("\n".join(all_lines), encoding="utf-8")

    print(f"\nГотово: {total_dps} точек, {total_cabinets} шкафов")
    print(f"Папка: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
