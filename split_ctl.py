"""
Скрипт для разделения PNR_Ventcontent.ctl на Ventcontent_<ШКАФ>.ctl (v4)

Ключевое исправление: find_block_end пропускает скобки внутри строк и комментариев.
Без этого класс KORF_AI (содержащий "{54,205,45}" в строках) съедал весь хвост файла.

Результат: scripts/Ventcontent_<ШКАФ>.ctl + split_ctl_report.txt
"""

import re
import csv
from pathlib import Path
from report_utils import write_report
from parse_utils import read_text_safe, find_mnemo_dirs, LCSMEMO_DIR, CTL_DIR, REPORT_DIR

CTL_FILE    = CTL_DIR / "PNR_Ventcontent.ctl"
SCRIPTS_DIR = CTL_DIR
REPORT_FILE = REPORT_DIR / "split_ctl_report.txt"


def find_block_end(text: str, start: int) -> int:
    """
    Находит конец блока по балансу { } от позиции start.
    Пропускает содержимое строк ("...") и комментариев (// и /* */).
    """
    depth = 0
    i = start
    length = len(text)

    while i < length:
        c = text[i]

        # Строковый литерал в двойных кавычках
        if c == '"':
            i += 1
            while i < length:
                if text[i] == '\\':
                    i += 2  # пропускаем escaped символ
                    continue
                if text[i] == '"':
                    break
                i += 1
            i += 1
            continue

        # Строковый литерал в одинарных кавычках
        if c == "'":
            i += 1
            while i < length:
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i] == "'":
                    break
                i += 1
            i += 1
            continue

        # Однострочный комментарий //
        if c == '/' and i + 1 < length and text[i + 1] == '/':
            i += 2
            while i < length and text[i] != '\n':
                i += 1
            i += 1
            continue

        # Многострочный комментарий /* ... */
        if c == '/' and i + 1 < length and text[i + 1] == '*':
            i += 2
            while i + 1 < length:
                if text[i] == '*' and text[i + 1] == '/':
                    i += 2
                    break
                i += 1
            continue

        # Фигурные скобки
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i

        i += 1

    return length - 1


def parse_ctl(text: str) -> dict:
    """Парсит .ctl файл."""
    lines = text.split('\n')

    result = {
        "uses_lines": [],
        "skifcontent_text": "",
        "class_blocks": {},
        "class_parents": {},
        "class_order": [],
        "setValueLib_text": "",
        "global_list": [],           # [(type, var, original_line), ...]
        "global_type_to_var": {},    # type -> var (последний если дубли)
        "mapping_entries": [],       # [(key, var), ...]
        "mapping_header": "",
        "classes_using_setValueLib": set(),  # классы, вызывающие setValueLib
    }

    # === #uses ===
    for line in lines:
        if line.strip().startswith('#uses'):
            result["uses_lines"].append(line)

    # === Классы ===
    class_pattern = re.compile(r'\bclass\s+(\w+)\s*(?::\s*(\w+))?\s*\{', re.DOTALL)
    class_positions = []
    for m in class_pattern.finditer(text):
        class_positions.append((m.start(), m.group(1), m.group(2)))

    # Для быстрой проверки "внутри класса ли позиция"
    class_ranges = []  # (start_pos, end_pos, name)

    for pos, name, parent in class_positions:
        brace_start = text.index('{', pos)
        body_end = find_block_end(text, brace_start)
        end = body_end + 1
        while end < len(text) and text[end] in ' \t\r':
            end += 1
        if end < len(text) and text[end] == ';':
            end += 1

        block_text = text[pos:end]
        class_ranges.append((pos, end, name))

        if name == "skifcontent":
            result["skifcontent_text"] = block_text
        else:
            result["class_blocks"][name] = block_text
            result["class_parents"][name] = parent or "skifcontent"
            result["class_order"].append(name)
            if "setValueLib" in block_text:
                result["classes_using_setValueLib"].add(name)

    # === setValueLib (вне классов) ===
    setval_pattern = re.compile(
        r'public\s+int\s+setValueLib\s*\([^)]*\)\s*\{', re.MULTILINE
    )
    for m in setval_pattern.finditer(text):
        pos = m.start()
        inside = any(cs <= pos <= ce for cs, ce, _ in class_ranges)
        if not inside:
            brace_pos = text.index('{', m.start())
            end_pos = find_block_end(text, brace_pos)
            result["setValueLib_text"] = text[m.start():end_pos + 1]
            break

    # === private global (вне классов) ===
    global_pattern = re.compile(r'(private\s+global\s+(\w+)\s+(\w+)\s*;)')
    for m in global_pattern.finditer(text):
        pos = m.start()
        inside = any(cs <= pos <= ce for cs, ce, _ in class_ranges)
        if not inside:
            gtype = m.group(2)
            gvar = m.group(3)
            result["global_list"].append((gtype, gvar, m.group(0).strip()))
            result["global_type_to_var"][gtype] = gvar

    # === mapping mapClassVent (вне классов) ===
    mapping_match = re.search(
        r'(public\s+const\s+mapping\s+mapClassVent\s*=\s*makeMapping\s*\()',
        text, re.MULTILINE
    )
    if mapping_match:
        pos = mapping_match.start()
        inside = any(cs <= pos <= ce for cs, ce, _ in class_ranges)
        if not inside:
            result["mapping_header"] = mapping_match.group(1)
            paren_start = mapping_match.end() - 1  # позиция (
            # Ищем закрывающую )
            depth = 1
            i = paren_start + 1
            while i < len(text) and depth > 0:
                if text[i] == '(':
                    depth += 1
                elif text[i] == ')':
                    depth -= 1
                i += 1
            content = text[paren_start + 1:i - 1]

            entry_pattern = re.compile(r'"(\w+)"\s*,\s*(\w+)')
            for em in entry_pattern.finditer(content):
                result["mapping_entries"].append((em.group(1), em.group(2)))

    return result


def get_cabinet_structs(cabinet_name: str) -> set[str]:
    """Собирает уникальные struct из CSV."""
    structs = set()
    cabinet_dir = LCSMEMO_DIR / cabinet_name
    if not cabinet_dir.exists():
        return structs
    for csv_file in cabinet_dir.rglob("*.csv"):
        csv_text = read_text_safe(csv_file)
        if csv_text is None:
            continue
        reader = csv.reader(csv_text.strip().split('\n'))
        next(reader, None)  # пропускаем заголовок
        for row in reader:
            if len(row) >= 5 and row[4].strip():
                structs.add(row[4].strip())
    return structs


def resolve_needed_classes(structs: set[str], parsed: dict) -> set[str]:
    """Определяет нужные классы."""
    needed = set()
    all_classes = set(parsed["class_blocks"].keys())

    # Обратные индексы
    var_to_type = {}
    for gtype, gvar, _ in parsed["global_list"]:
        var_to_type[gvar] = gtype

    key_to_var = {}
    for mkey, mvar in parsed["mapping_entries"]:
        key_to_var[mkey] = mvar

    for struct in structs:
        # 1. Прямое совпадение
        if struct in all_classes:
            needed.add(struct)

        # 2. struct = ключ маппинга → переменная → тип global → класс
        if struct in key_to_var:
            var = key_to_var[struct]
            if var in var_to_type:
                gtype = var_to_type[var]
                if gtype in all_classes:
                    needed.add(gtype)

        # 3. struct = тип global → класс
        if struct in parsed["global_type_to_var"] and struct in all_classes:
            needed.add(struct)

    # Родители
    for cls in list(needed):
        parent = parsed["class_parents"].get(cls)
        while parent and parent != "skifcontent" and parent in all_classes:
            needed.add(parent)
            parent = parsed["class_parents"].get(parent)

    return needed


def build_ctl(needed_classes: set[str], parsed: dict) -> str:
    """Собирает .ctl файл."""
    all_classes = set(parsed["class_blocks"].keys())
    excluded = all_classes - needed_classes

    # Переменные нужных global
    needed_vars = set()
    for gtype, gvar, _ in parsed["global_list"]:
        if gtype not in excluded:
            needed_vars.add(gvar)

    parts: list[str] = []

    # 1. #uses
    for line in parsed["uses_lines"]:
        parts.append(line)
    parts.append("")
    parts.append("")

    # 2. skifcontent
    parts.append(parsed["skifcontent_text"])
    parts.append("")

    # 3. Классы
    for cls_name in parsed["class_order"]:
        if cls_name in needed_classes:
            parts.append(parsed["class_blocks"][cls_name])
            parts.append("")

    # 4. setValueLib — только если хотя бы один нужный класс его вызывает
    needs_setValueLib = bool(needed_classes & parsed["classes_using_setValueLib"])
    if parsed["setValueLib_text"] and needs_setValueLib:
        parts.append(parsed["setValueLib_text"])
        parts.append("")
        parts.append("")

    # 5. private global
    for gtype, gvar, gline in parsed["global_list"]:
        if gtype not in excluded:
            parts.append(gline)
    parts.append("")

    # 6. mapping
    if parsed["mapping_entries"]:
        kept = [(k, v) for k, v in parsed["mapping_entries"]
                if k not in excluded and v in needed_vars]
        if kept:
            parts.append(parsed["mapping_header"])
            for i, (mkey, mvar) in enumerate(kept):
                if i < len(kept) - 1:
                    parts.append(f' "{mkey}", {mvar},')
                else:
                    parts.append(f'  "{mkey}", {mvar}')
            parts.append(");")
            parts.append("")

    return '\n'.join(parts)


def main():
    if not CTL_FILE.exists():
        print(f"Файл не найден: {CTL_FILE}")
        return

    print("Парсинг PNR_Ventcontent.ctl...")
    text = read_text_safe(CTL_FILE)
    if text is None:
        print(f"Не удалось прочитать: {CTL_FILE}")
        return

    parsed = parse_ctl(text)
    all_classes = set(parsed["class_blocks"].keys())

    print(f"  Классов: {len(all_classes)}")
    print(f"  Global: {len(parsed['global_list'])}")
    print(f"  Mapping: {len(parsed['mapping_entries'])}")

    # Валидация: ни один class не должен содержать private global
    for name in parsed["class_order"]:
        block = parsed["class_blocks"][name]
        if 'private global' in block:
            print(f"  ⚠ ОШИБКА: класс {name} содержит 'private global' — парсинг скобок сломан!")
            return
        if 'mapClassVent' in block:
            print(f"  ⚠ ОШИБКА: класс {name} содержит 'mapClassVent' — парсинг скобок сломан!")
            return

    print("  ✓ Валидация парсинга пройдена")

    if not LCSMEMO_DIR.exists():
        print(f"Папка не найдена: {LCSMEMO_DIR}")
        return

    cabinets = [d.name for d in find_mnemo_dirs()]
    print(f"\nШкафов: {len(cabinets)}")

    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    report: list[str] = []
    report.append("Отчёт по разделению PNR_Ventcontent.ctl (v4)")
    report.append("=" * 60)
    report.append(f"Оригинал: {len(all_classes)} классов, "
                   f"{len(parsed['global_list'])} global, "
                   f"{len(parsed['mapping_entries'])} mapping")
    report.append("")

    total = 0

    for cabinet in cabinets:
        structs = get_cabinet_structs(cabinet)
        if not structs:
            report.append(f"[{cabinet}] Нет struct — пропуск")
            continue

        needed = resolve_needed_classes(structs, parsed)
        excluded = all_classes - needed

        ctl_content = build_ctl(needed, parsed)

        output = SCRIPTS_DIR / f"Ventcontent_{cabinet}.ctl"
        ctl_bytes = ctl_content.replace('\r\n', '\n').encode("utf-8")
        output.write_bytes(ctl_bytes)
        total += 1

        kept_globals = sum(1 for gt, _, _ in parsed["global_list"] if gt not in excluded)
        needed_vars = set()
        for gt, gv, _ in parsed["global_list"]:
            if gt not in excluded:
                needed_vars.add(gv)
        kept_mapping = sum(1 for mk, mv in parsed["mapping_entries"]
                          if mk not in excluded and mv in needed_vars)

        report.append(f"[{cabinet}]")
        report.append(f"  struct: {len(structs)}")
        report.append(f"  классов: {len(needed)} / {len(all_classes)}")
        report.append(f"  global:  {kept_globals} / {len(parsed['global_list'])}")
        report.append(f"  mapping: {kept_mapping} / {len(parsed['mapping_entries'])}")
        needs_svl = bool(needed & parsed["classes_using_setValueLib"])
        report.append(f"  setValueLib: {'да' if needs_svl else 'нет'}")

        if needed:
            report.append("  Включены:")
            for c in sorted(needed):
                report.append(f"    ✓ {c}")

        report.append(f"  → {output.name}")
        report.append("")

        print(f"  [{cabinet}] классов: {len(needed)}, "
              f"global: {kept_globals}, mapping: {kept_mapping}")

    report.append("=" * 60)
    report.append(f"Сгенерировано: {total}")

    write_report(REPORT_FILE, report)

    print(f"\nСгенерировано: {total} в {SCRIPTS_DIR}/")
    print(f"Отчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
