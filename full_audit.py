"""
Полный аудит XML объектов — все способы экранирования и паттерны использования классов.

Ищет:
1. ВСЕ варианты кавычек вокруг struct (какие форматы реально используются)
2. ВСЕ строки содержащие "struct" — показывает точный контекст
3. ВСЕ создания объектов классов (CLASS_NAME var;) — даже вне if-struct
4. ВСЕ #uses строки — какие форматы ссылок на скрипты

Результат: full_audit_report.txt
"""

import re
from pathlib import Path
from collections import Counter
from report_utils import write_report
from parse_utils import read_text_safe, PANELS_DIR, OBJECTS_DIR, REPORT_DIR

REPORT_FILE = REPORT_DIR / "full_audit_report.txt"


def extract_scripts(xml_file: Path) -> list[str]:
    """Извлекает все скриптовые секции из XML."""
    text = read_text_safe(xml_file)
    if text is None:
        return []

    scripts = []

    # CDATA
    for m in re.finditer(r'<!\[CDATA\[(.*?)\]\]>', text, re.DOTALL):
        scripts.append(("CDATA", m.group(1)))

    # Атрибут value="..." с кодом
    for m in re.finditer(r'(?:value|text)\s*=\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL):
        content = m.group(1)
        if 'struct' in content or 'class' in content or '#uses' in content:
            scripts.append(("ATTR", content))

    # Всё что между тегами script (не CDATA, бывает inline)
    for m in re.finditer(r'<script[^>]*>((?:(?!<!\[CDATA\[).)*?)</script>', text, re.DOTALL):
        content = m.group(1).strip()
        if content and 'struct' in content:
            scripts.append(("INLINE", content))

    # Если ничего не нашли через паттерны, ищем struct в raw тексте
    if not any('struct' in s[1] for s in scripts) and 'struct' in text:
        scripts.append(("RAW", text))

    return scripts


def main():
    if not OBJECTS_DIR.exists():
        print(f"Папка не найдена: {OBJECTS_DIR}")
        return

    report: list[str] = []
    report.append("ПОЛНЫЙ АУДИТ XML ОБЪЕКТОВ")
    report.append("=" * 70)
    report.append("")

    # Счётчики
    quote_styles = Counter()       # формат кавычек в struct проверках
    struct_patterns = Counter()    # полный паттерн if-struct
    class_instantiations = []      # CLASS var; вне if-struct
    uses_formats = Counter()       # форматы #uses
    all_struct_lines = []          # все строки с struct для ручного обзора
    files_with_struct = 0

    for xml_file in sorted(OBJECTS_DIR.rglob("*.xml")):
        rel = str(xml_file.relative_to(PANELS_DIR)).replace("\\", "/")
        scripts = extract_scripts(xml_file)

        file_has_struct = False

        for src_type, script in scripts:
            lines = script.split('\n')

            for line_idx, line in enumerate(lines):
                # === Поиск всех struct проверок ===
                if 'struct' in line:
                    file_has_struct = True
                    stripped = line.strip()

                    # Определяем формат кавычек
                    if '&quot;struct&quot;' in line:
                        quote_styles["&quot;"] += 1
                    if '\\"struct\\"' in line:
                        quote_styles['\\\"'] += 1
                    if re.search(r'(?<!\\)(?<!&quot)"struct"', line):
                        quote_styles['"'] += 1
                    if "&apos;" in line and 'struct' in line:
                        quote_styles["&apos;"] += 1
                    if "&#34;" in line and 'struct' in line:
                        quote_styles["&#34;"] += 1
                    if "&#x22;" in line and 'struct' in line:
                        quote_styles["&#x22;"] += 1

                    # Полный паттерн: if / else if / switch
                    if re.search(r'if\s*\(.*struct', stripped):
                        if re.search(r'else\s+if', stripped):
                            struct_patterns["else if"] += 1
                        else:
                            struct_patterns["if"] += 1

                        # Извлекаем имя класса
                        cls_match = (
                            re.search(r'==\s*&quot;(\w+)&quot;', stripped) or
                            re.search(r'==\s*\\"(\w+)\\"', stripped) or
                            re.search(r'==\s*"(\w+)"', stripped) or
                            re.search(r'==\s*&#34;(\w+)&#34;', stripped)
                        )
                        cls_name = cls_match.group(1) if cls_match else "???"

                        all_struct_lines.append((rel, line_idx + 1, src_type, cls_name, stripped[:150]))

                    elif 'switch' in stripped and 'struct' in stripped:
                        struct_patterns["switch"] += 1
                        all_struct_lines.append((rel, line_idx + 1, src_type, "SWITCH", stripped[:150]))

                    elif 'struct' in stripped and 'if' not in stripped and 'switch' not in stripped:
                        # struct используется не в if/switch
                        if not stripped.startswith('//') and 'settings[' in stripped:
                            all_struct_lines.append((rel, line_idx + 1, src_type, "OTHER", stripped[:150]))

                # === #uses строки ===
                if '#uses' in line:
                    stripped = line.strip()
                    if '&quot;' in stripped:
                        uses_formats["&quot;...&quot;"] += 1
                    elif '\\"' in stripped:
                        uses_formats['\\"...\\"'] += 1
                    elif '"' in stripped:
                        uses_formats['"..."'] += 1

        if file_has_struct:
            files_with_struct += 1

    # === ОТЧЁТ ===
    report.append("1. ФОРМАТЫ КАВЫЧЕК В STRUCT ПРОВЕРКАХ")
    report.append("-" * 40)
    for style, count in quote_styles.most_common():
        report.append(f"  {style:15s}: {count}")
    report.append("")

    report.append("2. ПАТТЕРНЫ ПРОВЕРКИ STRUCT")
    report.append("-" * 40)
    for pattern, count in struct_patterns.most_common():
        report.append(f"  {pattern:15s}: {count}")
    report.append(f"  Файлов с struct: {files_with_struct}")
    report.append("")

    report.append("3. ФОРМАТЫ #USES")
    report.append("-" * 40)
    for fmt, count in uses_formats.most_common():
        report.append(f"  {fmt:20s}: {count}")
    report.append("")

    report.append("4. ВСЕ STRUCT ПРОВЕРКИ (полный список)")
    report.append("-" * 40)

    # Группируем по классу
    cls_counter = Counter()
    for rel, line, src, cls, text_line in all_struct_lines:
        cls_counter[cls] += 1

    report.append(f"  Уникальных классов в struct проверках: {len(cls_counter)}")
    report.append("")
    for cls, count in cls_counter.most_common():
        report.append(f"  {cls}: {count} раз")
    report.append("")

    report.append("  Детали (файл, строка, формат, класс):")
    for rel, line, src, cls, text_line in all_struct_lines:
        report.append(f"    [{src:5s}] {rel}:{line} → {cls}")
    report.append("")

    report.append("=" * 70)
    report.append("ИТОГО:")
    report.append(f"  Форматов кавычек: {len(quote_styles)}")
    report.append(f"  Паттернов struct: {len(struct_patterns)}")
    report.append(f"  Форматов #uses:   {len(uses_formats)}")

    if len(quote_styles) > 3:
        report.append("")
        report.append("  ⚠ ВНИМАНИЕ: найдены экзотические форматы кавычек!")

    write_report(REPORT_FILE, report)

    print("\n".join(report[-10:]))
    print(f"\nОтчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
