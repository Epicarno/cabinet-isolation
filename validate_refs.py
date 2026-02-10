"""
Скрипт-валидатор: проверяет, что все файлы, на которые ссылаются XML, реально существуют.

Игнорирует ссылки внутри комментариев:
  - однострочных //
  - многострочных /* ... */

Показывает цепочку на одну глубину назад:
  ✗ недостающий_файл
    ← объект, который ссылается на него
      ← мнемосхема, которая использует этот объект

Результат: missing_files_report.txt
"""

import re
from pathlib import Path
from report_utils import write_report
from parse_utils import read_text_safe, PANELS_DIR, OBJECTS_DIR, VISION_DIR, LCSMEMO_DIR, REPORT_DIR

REPORT_FILE = REPORT_DIR / "missing_files_report.txt"

PATTERN = re.compile(r'objects/[^\s"\'<>]+?\.xml')

# Многострочные комментарии /* ... */
MULTI_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)


def strip_comments(text: str) -> str:
    """Убирает комментарии из текста, оставляя только рабочий код.
    Не трогает // внутри строковых литералов (например URL)."""
    # 1. Убираем многострочные /* ... */
    text = MULTI_COMMENT.sub('', text)

    # 2. Убираем однострочные // (но не внутри строк)
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        result = []
        in_string = False
        string_char = None
        i = 0
        while i < len(line):
            c = line[i]
            if in_string:
                result.append(c)
                if c == '\\' and i + 1 < len(line):
                    result.append(line[i + 1])
                    i += 2
                    continue
                if c == string_char:
                    in_string = False
                i += 1
            else:
                if c in ('"', "'"):
                    in_string = True
                    string_char = c
                    result.append(c)
                    i += 1
                elif c == '/' and i + 1 < len(line) and line[i + 1] == '/':
                    break  # комментарий — обрезаем остаток строки
                else:
                    result.append(c)
                    i += 1
        cleaned.append(''.join(result))

    return '\n'.join(cleaned)


def build_reverse_map() -> dict[str, set[str]]:
    """
    Строит обратную карту: referenced_path -> set(файлы, которые на него ссылаются).
    Ссылки внутри комментариев игнорируются.
    """
    reverse: dict[str, set[str]] = {}

    scan_dirs: list[Path] = []

    # Мнемосхемы
    if LCSMEMO_DIR.exists():
        for d in LCSMEMO_DIR.iterdir():
            if d.is_dir():
                scan_dirs.append(d)

    # Объекты
    if OBJECTS_DIR.exists():
        for d in OBJECTS_DIR.iterdir():
            if d.is_dir() and d.name.startswith("objects_"):
                scan_dirs.append(d)

    for scan_dir in scan_dirs:
        for xml_file in scan_dir.rglob("*.xml"):
            text = read_text_safe(xml_file)
            if text is None:
                continue

            file_rel = str(xml_file.relative_to(PANELS_DIR)).replace("\\", "/")

            # Убираем комментарии перед поиском ссылок
            clean_text = strip_comments(text)

            for match in PATTERN.finditer(clean_text):
                ref_path = match.group(0)
                if ref_path not in reverse:
                    reverse[ref_path] = set()
                reverse[ref_path].add(file_rel)

    return reverse


def main():
    print("Построение карты ссылок (комментарии игнорируются)...")
    reverse_map = build_reverse_map()

    # Находим недостающие файлы
    missing: dict[str, set[str]] = {}
    for ref_path, sources in reverse_map.items():
        full_path = PANELS_DIR / ref_path
        if not full_path.exists():
            missing[ref_path] = sources

    # Отчёт
    report_lines: list[str] = []
    report_lines.append("Отчёт: файлы, на которые есть ссылки, но которые не существуют")
    report_lines.append("(ссылки внутри комментариев // и /* */ игнорируются)")
    report_lines.append("=" * 70)
    report_lines.append("")

    if missing:
        report_lines.append(f"Всего недостающих файлов: {len(missing)}")
        report_lines.append("")

        for missing_file in sorted(missing.keys()):
            direct_sources = sorted(missing[missing_file])
            report_lines.append(f"✗ {missing_file}")

            for src in direct_sources:
                report_lines.append(f"  ← {src}")

                # Одна глубина назад: кто ссылается на src?
                parents = reverse_map.get(src, set()).copy()
                parents.discard(src)

                seen_parents: set[str] = set()
                for parent in sorted(parents):
                    if parent not in seen_parents:
                        seen_parents.add(parent)
                        report_lines.append(f"    ← {parent}")

            report_lines.append("")

        # Консольный вывод
        print(f"\nНайдено недостающих файлов: {len(missing)}")
        for missing_file in sorted(missing.keys()):
            direct_sources = sorted(missing[missing_file])
            print(f"\n  ✗ {missing_file}")
            for src in direct_sources:
                print(f"    ← {src}")
                parents = reverse_map.get(src, set()).copy()
                parents.discard(src)
                for parent in sorted(parents):
                    print(f"      ← {parent}")
    else:
        report_lines.append("Все ссылки ведут на существующие файлы. Всё в порядке!")
        print("\nВсё чисто — все файлы на месте!")

    write_report(REPORT_FILE, report_lines)

    print(f"\nОтчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
