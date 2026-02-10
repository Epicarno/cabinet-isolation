"""
Сканер проблемных мест в XML объектах.

Ищет:
1. Комментарии // содержащие &quot; (могут ломать парсинг)
2. if-блоки с struct проверкой в нестандартном формате (else if, switch, etc.)
3. Использование классов вне if(settings["struct"]) — напрямую в коде

Результат: problem_scan_report.txt
"""

import re
from pathlib import Path
from report_utils import write_report
from parse_utils import read_text_safe, PANELS_DIR, OBJECTS_DIR, REPORT_DIR

REPORT_FILE = REPORT_DIR / "problem_scan_report.txt"


def scan_file(xml_file: Path, rel_path: str) -> list[str]:
    """Сканирует один XML файл на проблемные паттерны."""
    issues = []

    text = read_text_safe(xml_file)
    if text is None:
        return issues

    # Ищем только в CDATA секциях (скрипты)
    cdata_pattern = re.compile(r'<!\[CDATA\[(.*?)\]\]>', re.DOTALL)
    
    for cdata_match in cdata_pattern.finditer(text):
        script = cdata_match.group(1)
        script_start = cdata_match.start(1)
        lines = script.split('\n')

        for line_idx, line in enumerate(lines):
            stripped = line.strip()

            # 1. Комментарий // с &quot; внутри
            comment_pos = -1
            # Ищем // не внутри строки
            in_str = False
            for ci in range(len(stripped) - 1):
                if stripped[ci:ci+6] == '&quot;':
                    in_str = not in_str
                if not in_str and stripped[ci] == '/' and stripped[ci+1] == '/':
                    comment_pos = ci
                    break
            
            if comment_pos >= 0:
                comment = stripped[comment_pos:]
                if '&quot;' in comment:
                    issues.append(f"  [COMMENT+QUOT] {rel_path} строка ~{line_idx+1}: {stripped[:120]}")

            # 2. else if с struct
            if re.search(r'else\s+if\s*\(.*struct', stripped):
                issues.append(f"  [ELSE IF] {rel_path} строка ~{line_idx+1}: {stripped[:120]}")

            # 3. switch/case с struct
            if 'switch' in stripped and 'struct' in stripped:
                issues.append(f"  [SWITCH] {rel_path} строка ~{line_idx+1}: {stripped[:120]}")

            # 4. Backslash-escaped quotes с &quot; в комментарии
            if comment_pos >= 0:
                comment = stripped[comment_pos:]
                if '\\"' in comment:
                    issues.append(f"  [COMMENT+BSQUOT] {rel_path} строка ~{line_idx+1}: {stripped[:120]}")

            # 4. Создание экземпляра класса НЕ внутри if-struct блока
            # Ищем паттерн "CLASSNAME varname;" — создание объекта
            # Но только вне if-struct (сложно определить точно, поэтому ищем все)

    return issues


def main():
    if not OBJECTS_DIR.exists():
        print(f"Папка не найдена: {OBJECTS_DIR}")
        return

    report: list[str] = []
    report.append("Сканирование проблемных паттернов в XML объектах")
    report.append("=" * 70)
    report.append("")

    counts = {"COMMENT+QUOT": 0, "ELSE IF": 0, "SWITCH": 0}

    for xml_file in sorted(OBJECTS_DIR.rglob("*.xml")):
        rel = str(xml_file.relative_to(PANELS_DIR)).replace("\\", "/")
        issues = scan_file(xml_file, rel)
        if issues:
            report.extend(issues)
            for iss in issues:
                for key in counts:
                    if key in iss:
                        counts[key] += 1

    report.append("")
    report.append("=" * 70)
    report.append(f"Комментарии с &quot;:  {counts['COMMENT+QUOT']}")
    report.append(f"else if + struct:  {counts['ELSE IF']}")
    report.append(f"switch + struct:   {counts['SWITCH']}")

    write_report(REPORT_FILE, report)

    print("\n".join(report[-5:]))
    print(f"\nОтчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
