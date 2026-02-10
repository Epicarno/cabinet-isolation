"""
Проверка: не удалит ли cleanup_classes.py if-блоки для классов из ДРУГИХ скриптов.

Для каждого объекта в objects_<ШКАФ>/:
1. Собирает все #uses → список подключённых скриптов
2. Собирает все struct-классы из if-блоков
3. Проверяет: если класса нет в Ventcontent — может он из другого скрипта?

Результат: other_scripts_check.txt
"""

import re
import json
from pathlib import Path
from report_utils import write_report
from parse_utils import read_text_safe, find_cabinet_dirs, PANELS_DIR, OBJECTS_DIR, CTL_DIR, REPORT_DIR

SCRIPTS_DIR  = CTL_DIR
SCRIPTS_LIBS = CTL_DIR  # где лежат .ctl
REPORT_FILE  = REPORT_DIR / "other_scripts_check.txt"
JSON_FILE    = REPORT_DIR / "other_scripts.json"


def get_classes_from_ctl(ctl_path: Path) -> set[str]:
    """Извлекает имена классов из .ctl файла."""
    if not ctl_path.exists():
        return set()
    text = read_text_safe(ctl_path)
    if text is None:
        return set()
    return {m.group(1) for m in re.finditer(r'\bclass\s+(\w+)', text)}


def extract_uses(text: str) -> list[str]:
    """Извлекает имена скриптов из #uses."""
    uses = []
    patterns = [
        re.compile(r'#uses\s+&quot;([^&]+)&quot;'),
        re.compile(r'#uses\s+\\"([^\\]+)\\"'),
        re.compile(r'#uses\s+"([^"]+)"'),
    ]
    for p in patterns:
        for m in p.finditer(text):
            uses.append(m.group(1))
    return uses


def extract_struct_classes(text: str) -> set[str]:
    """Извлекает имена классов из if(settings["struct"] == "CLASS")."""
    classes = set()
    patterns = [
        re.compile(r'if\s*\(.*?struct.*?==\s*&quot;(\w+)&quot;'),
        re.compile(r'if\s*\(.*?struct.*?==\s*\\"(\w+)\\"'),
        re.compile(r'if\s*\(.*?struct.*?==\s*"(\w+)"'),
    ]
    for p in patterns:
        for m in p.finditer(text):
            classes.add(m.group(1))
    return classes


def main():
    if not OBJECTS_DIR.exists():
        print(f"Папка не найдена: {OBJECTS_DIR}")
        return

    report: list[str] = []
    report.append("Проверка: классы из других скриптов (не Ventcontent)")
    report.append("=" * 70)
    report.append("")

    problems = 0
    # Защищённые классы: класс не из Ventcontent, но из другого подключённого скрипта
    protected: dict[str, dict[str, str]] = {}  # {cabinet: {class: script_name}}

    cabinet_dirs = find_cabinet_dirs(OBJECTS_DIR)

    for cab_dir in cabinet_dirs:
        cabinet_name = cab_dir.name.replace("objects_", "", 1)
        ctl_file = SCRIPTS_DIR / f"Ventcontent_{cabinet_name}.ctl"
        vent_classes = get_classes_from_ctl(ctl_file)

        cab_problems: list[str] = []

        for xml_file in sorted(cab_dir.rglob("*.xml")):
            text = read_text_safe(xml_file)
            if text is None:
                continue

            if 'struct' not in text:
                continue

            struct_classes = extract_struct_classes(text)
            if not struct_classes:
                continue

            uses = extract_uses(text)
            rel = str(xml_file.relative_to(PANELS_DIR)).replace("\\", "/")

            # Собираем классы из ВСЕХ подключённых скриптов
            other_scripts_classes: dict[str, set[str]] = {}
            for use in uses:
                script_name = use.split("/")[-1]
                if script_name.startswith("Ventcontent_"):
                    continue  # это наш скрипт, пропускаем

                # Ищем файл
                candidates = [
                    SCRIPTS_LIBS / script_name,
                    SCRIPTS_LIBS / (script_name + ".ctl") if not script_name.endswith(".ctl") else None,
                ]
                for cand in candidates:
                    if cand and cand.exists():
                        cls = get_classes_from_ctl(cand)
                        if cls:
                            other_scripts_classes[script_name] = cls
                        break

            # Проверяем каждый struct-класс
            for cls in sorted(struct_classes):
                in_vent = cls in vent_classes
                in_other = None
                for sname, scls in other_scripts_classes.items():
                    if cls in scls:
                        in_other = sname
                        break

                if not in_vent and in_other:
                    cab_problems.append(
                        f"  ⚠ {rel}: класс {cls} — НЕ в Ventcontent, но ЕСТЬ в {in_other}"
                    )
                    problems += 1
                    # Запоминаем для JSON
                    if cabinet_name not in protected:
                        protected[cabinet_name] = {}
                    protected[cabinet_name][cls] = in_other
                elif not in_vent and not in_other:
                    # Нет нигде — cleanup_classes удалит, и правильно
                    pass

        if cab_problems:
            report.append(f"[{cabinet_name}]")
            report.extend(cab_problems)
            report.append("")

    if problems == 0:
        report.append("✓ Проблем не найдено — все struct-классы из Ventcontent")
    else:
        report.append(f"⚠ Найдено проблем: {problems}")
        report.append("  Эти if-блоки cleanup_classes.py удалит ОШИБОЧНО!")
        report.append("  Нужно добавить исключения или собирать классы из всех #uses")

    report.append("")

    write_report(REPORT_FILE, report)

    # Сохраняем JSON для cleanup_classes.py
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(protected, f, ensure_ascii=False, indent=2)
    print(f"JSON: {JSON_FILE} (защищённых классов: {sum(len(v) for v in protected.values())})")

    if problems:
        print(f"⚠ Найдено {problems} проблемных классов из других скриптов!")
    else:
        print("✓ Все struct-классы из Ventcontent, проблем нет")
    print(f"Отчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
