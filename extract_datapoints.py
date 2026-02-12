"""
Извлечение всех уникальных точек данных (DP) из мнемосхем.

Два источника точек:
  1) XML:  атрибут Name="ШКАФ>МНЕМО>ТИП>DP" в <reference> (формат SHD-шкафов)
  2) CSV:  колонки refName и dpName (формат SHUOD, SHKZIAV, SHUVO и др.)

Результат:
  reports/datapoints/
    _all.txt                     ← все точки всех шкафов
    SHD_03_1.txt                 ← точки одного шкафа (XML + CSV)
    SHUOD_03_1.txt               ← точки из CSV
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


def extract_from_xml(xml_path: Path) -> list[str]:
    """Извлекает все точки данных из одного XML (по Name с >)."""
    text = read_text_safe(xml_path)
    if text is None:
        return []
    return DP_PATTERN.findall(text)


def extract_from_csv(csv_path: Path, cabinet: str) -> list[str]:
    """Извлекает точки данных из CSV-файла (колонки refName и dpName).

    Возвращает все уникальные непустые значения из обоих колонок.
    dpName может содержать несколько точек через '|'.
    Фильтрует: берёт только точки, refName/dpName которых принадлежат
    текущему шкафу (начинаются с его имени), чтобы не подхватить
    чужие CSV-файлы, случайно лежащие в папке (напр. SHUOD_03_1.csv
    внутри SHD_03_1/).
    """
    try:
        text = csv_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    points: list[str] = []
    for line in text.strip().split("\n")[1:]:  # пропускаем заголовок
        parts = line.split(",")
        if len(parts) < 2:
            continue
        ref_name = parts[0].strip()
        dp_name = parts[1].strip()

        # Хотя бы одно из имён должно принадлежать текущему шкафу
        ref_ok = ref_name.startswith(cabinet)
        dp_ok = dp_name.startswith(cabinet)
        if not ref_ok and not dp_ok:
            continue

        if ref_name:
            points.append(ref_name)
        if dp_name:
            # dpName может быть "DP1|DP2" — несколько точек
            for dp in dp_name.split("|"):
                dp = dp.strip()
                if dp and dp != ref_name:
                    points.append(dp)
    return points


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
        csv_points: dict[str, list[str]] = defaultdict(list)

        # 1) Из XML — точки с > в Name=""
        for xml_file in sorted(cab_dir.rglob("*.xml")):
            points = extract_from_xml(xml_file)
            mnemo_name = xml_file.stem
            for p in points:
                by_mnemo[mnemo_name].append(p)

        # 2) Из CSV — refName + dpName (только точки этого шкафа)
        for csv_file in sorted(cab_dir.glob("*.csv")):
            points = extract_from_csv(csv_file, cabinet)
            mnemo_name = csv_file.stem
            for p in points:
                csv_points[mnemo_name].append(p)

        # Объединяем: точки из CSV, которых нет в XML
        xml_all = set()
        for pts in by_mnemo.values():
            xml_all.update(pts)

        csv_new = 0
        for mnemo, pts in csv_points.items():
            for p in pts:
                if p not in xml_all:
                    by_mnemo[mnemo].append(p)
                    csv_new += 1

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

        csv_tag = f" (+{csv_new} из CSV)" if csv_new else ""
        print(f"  [{cabinet}] {len(cab_unique)} точек, {len(by_mnemo)} мнемосхем{csv_tag} → {cab_file.name}")

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
