"""
Удаление if-блоков с несуществующими классами из объектов.

Для каждого шкафа:
1. Парсит Ventcontent_<ШКАФ>.ctl → список доступных классов
2. В XML объектах ищет блоки вида:
     if (settings["struct"] == "CLASS_NAME") { ... }
     if(settings["struct"] == "CLASS_NAME"){ ... }
   (включая &quot; вариант в escaped XML)
3. Удаляет целые if-блоки для классов, которых нет в скрипте шкафа

Результат: cleanup_classes_report.txt
"""

import re
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from report_utils import write_report
from parse_utils import find_matching_brace, read_text_safe, find_cabinet_dirs, PANELS_DIR, OBJECTS_DIR, CTL_DIR, REPORT_DIR

# Windows cp866/cp1251 ломает Unicode → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPTS_DIR = CTL_DIR
REPORT_FILE = REPORT_DIR / "cleanup_classes_report.txt"
JSON_FILE   = REPORT_DIR / "other_scripts.json"


def get_classes_from_ctl(ctl_file: Path) -> set[str]:
    """Извлекает имена классов из Ventcontent_*.ctl."""
    text = read_text_safe(ctl_file)
    if text is None:
        return set()

    classes = set()
    for m in re.finditer(r'\bclass\s+(\w+)', text):
        classes.add(m.group(1))
    return classes


def remove_unused_class_blocks(text: str, available_classes: set[str]) -> tuple[str, list[str]]:
    """
    Ищет if-блоки проверяющие struct и удаляет те, чьи классы отсутствуют.
    Возвращает (новый_текст, список_удалённых_классов).
    """
    removed = []

    # Паттерн для поиска: if (settings["struct"] == "CLASS") или if(settings[&quot;struct&quot;] == &quot;CLASS&quot;)
    # Варианты: с/без пробелов, с/без &quot;
    patterns = [
        # Escaped XML: &quot;struct&quot; ... &quot;CLASS&quot;
        re.compile(
            r'if\s*\(\s*settings\s*\[\s*&quot;struct&quot;\s*\]\s*==\s*&quot;(\w+)&quot;\s*\)'
        ),
        # Обычный: "struct" ... "CLASS"
        re.compile(
            r'if\s*\(\s*settings\s*\[\s*"struct"\s*\]\s*==\s*"(\w+)"\s*\)'
        ),
        # Backslash-escaped: \"struct\" ... \"CLASS\"
        re.compile(
            r'if\s*\(\s*settings\s*\[\s*\\"struct\\"\s*\]\s*==\s*\\"(\w+)\\"\s*\)'
        ),
    ]

    # Собираем все if-блоки с позициями (обрабатываем с конца чтобы не сбивать индексы)
    blocks_to_remove = []

    for pattern in patterns:
        for m in pattern.finditer(text):
            class_name = m.group(1)
            if class_name in available_classes:
                continue  # класс есть, оставляем

            # Ищем { после if(...)
            if_start = m.start()
            brace_search_start = m.end()

            # Пропускаем пробелы/переносы/комментарии до {
            j = brace_search_start
            while j < len(text):
                # Пробелы и переносы
                if text[j] in ' \t\r\n':
                    j += 1
                    continue
                # Однострочный комментарий //
                if text[j] == '/' and j + 1 < len(text) and text[j + 1] == '/':
                    while j < len(text) and text[j] != '\n':
                        j += 1
                    continue
                break

            if j >= len(text) or text[j] != '{':
                continue  # нет {, пропускаем

            brace_end = find_matching_brace(text, j)
            if brace_end == -1:
                continue

            # Расширяем удаление: пустые строки перед if и после }
            block_start = if_start
            block_end = brace_end + 1

            # Захватываем пустые строки/пробелы перед if
            while block_start > 0 and text[block_start - 1] in ' \t':
                block_start -= 1

            # Захватываем перенос строки перед if
            if block_start > 0 and text[block_start - 1] == '\n':
                block_start -= 1

            # Захватываем пустые строки после }
            while block_end < len(text) and text[block_end] in ' \t\r':
                block_end += 1
            if block_end < len(text) and text[block_end] == '\n':
                block_end += 1

            blocks_to_remove.append((block_start, block_end, class_name))

    if not blocks_to_remove:
        return text, removed

    # Сортируем по позиции с конца
    blocks_to_remove.sort(key=lambda x: x[0], reverse=True)

    # Убираем пересечения (оставляем только уникальные)
    filtered = []
    for start, end, cls in blocks_to_remove:
        overlap = False
        for fs, fe, _ in filtered:
            if start < fe and end > fs:
                overlap = True
                break
        if not overlap:
            filtered.append((start, end, cls))

    # Удаляем блоки
    for start, end, cls in filtered:
        text = text[:start] + text[end:]
        removed.append(cls)

    return text, removed


def main():
    if not OBJECTS_DIR.exists():
        print(f"Папка не найдена: {OBJECTS_DIR}")
        return

    cabinet_dirs = find_cabinet_dirs(OBJECTS_DIR)

    if not cabinet_dirs:
        print("Папки objects/objects_<ШКАФ>/ не найдены.")
        return

    report: list[str] = []
    report.append("Отчёт: удаление if-блоков для отсутствующих классов")
    report.append("=" * 70)
    report.append("")

    # Загружаем защищённые классы из JSON (сгенерирован check_other_scripts.py)
    protected_map: dict[str, dict[str, str]] = {}
    if JSON_FILE.exists():
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                protected_map = json.load(f)
            total_prot = sum(len(v) for v in protected_map.values())
            print(f"Загружено защищённых классов: {total_prot} (из {JSON_FILE.name})")
            report.append(f"Защищённых классов (из других скриптов): {total_prot}")
            report.append("")
        except Exception as e:
            print(f"⚠ Не удалось прочитать {JSON_FILE}: {e}")
            report.append(f"⚠ Не удалось прочитать {JSON_FILE.name}: {e}")
            report.append("")
    else:
        print(f"ℹ {JSON_FILE.name} не найден — защита классов отключена")
        report.append("ℹ other_scripts.json не найден — защита классов отключена")
        report.append("Запустите check_other_scripts.py перед cleanup_classes.py")
        report.append("")

    total_files = 0
    total_blocks = 0

    for cab_dir in cabinet_dirs:
        cabinet_name = cab_dir.name.replace("objects_", "", 1)
        ctl_file = SCRIPTS_DIR / f"Ventcontent_{cabinet_name}.ctl"

        if not ctl_file.exists():
            report.append(f"[{cabinet_name}] Скрипт не найден — пропуск")
            continue

        available = get_classes_from_ctl(ctl_file)

        # Добавляем защищённые классы из других скриптов
        protected_classes = set(protected_map.get(cabinet_name, {}).keys())
        if protected_classes:
            report.append(f"  Защищено ({len(protected_classes)}): {', '.join(sorted(protected_classes))}")
        available = available | protected_classes

        cab_files = 0
        cab_blocks = 0
        cab_report: list[str] = []

        for xml_file in sorted(cab_dir.rglob("*.xml")):
            text = read_text_safe(xml_file)
            if text is None:
                continue

            # Проверяем есть ли struct проверки вообще
            if 'struct' not in text:
                continue

            new_text, removed = remove_unused_class_blocks(text, available)

            if removed:
                xml_file.write_text(new_text, encoding="utf-8")
                file_rel = str(xml_file.relative_to(PANELS_DIR)).replace("\\", "/")
                cab_report.append(f"    [✓] {file_rel}")
                for cls in removed:
                    cab_report.append(f"        ✗ {cls}")
                cab_files += 1
                cab_blocks += len(removed)

        if cab_files:
            report.append(f"[{cabinet_name}] файлов: {cab_files}, блоков удалено: {cab_blocks}")
            report.append(f"  Доступные классы ({len(available)}): {', '.join(sorted(available))}")
            report.extend(cab_report)
            report.append("")

        total_files += cab_files
        total_blocks += cab_blocks

        if cab_files:
            print(f"  [{cabinet_name}] {cab_files} файлов, {cab_blocks} блоков удалено")

    report.append("=" * 70)
    report.append(f"Всего файлов: {total_files}")
    report.append(f"Всего блоков удалено: {total_blocks}")

    write_report(REPORT_FILE, report)

    print(f"\nВсего: {total_files} файлов, {total_blocks} блоков удалено")
    print(f"Отчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
