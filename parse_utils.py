"""
Общие утилиты и пути для пайплайна Project Split.

Пути:
- SCRIPT_DIR  — папка с Python-скриптами (Modules/scripts/)
- VENT_DIR    — корень ventcontent (Modules/ventcontent/)
- PANELS_DIR  — данные проекта (ventcontent/panels/)
- OBJECTS_DIR — объекты XML (ventcontent/panels/objects/)
- VISION_DIR  — мнемосхемы (ventcontent/panels/vision/)
- LCSMEMO_DIR — шкафы (ventcontent/panels/vision/LCSMnemo/)
- CTL_DIR     — скрипты WinCC OA (ventcontent/scripts/libs/objLogic/)
- REPORT_DIR  — папка отчётов (Modules/reports/)
- OLD_MNEMO_DIR — бэкап оригинальных мнемосхем (Modules/old_mnemo/)

Утилиты:
- read_text_safe() — чтение файла с fallback по кодировкам
- find_matching_brace() — поиск закрывающей } с учётом строк/комментариев
- load_active_cabinets() — чтение cabinets.txt (None = все)
- find_cabinet_dirs() — поиск папок objects_<ШКАФ>/ с фильтрацией
- find_mnemo_dirs() — поиск папок мнемосхем с фильтрацией
"""

from pathlib import Path

# === Общие пути проекта ===
SCRIPT_DIR  = Path(__file__).resolve().parent               # Modules/scripts/
VENT_DIR    = SCRIPT_DIR.parent / "ventcontent"             # Modules/ventcontent/
PANELS_DIR  = VENT_DIR / "panels"                           # ventcontent/panels/
OBJECTS_DIR = PANELS_DIR / "objects"                         # panels/objects/
VISION_DIR  = PANELS_DIR / "vision"                         # panels/vision/
LCSMEMO_DIR = VISION_DIR / "LCSMnemo"                       # vision/LCSMnemo/
CTL_DIR     = VENT_DIR / "scripts" / "libs" / "objLogic"    # scripts/libs/objLogic/
REPORT_DIR  = SCRIPT_DIR.parent / "reports"                 # Modules/reports/
OLD_MNEMO_DIR = SCRIPT_DIR.parent / "old_mnemo"             # Modules/old_mnemo/


def read_text_safe(path: Path) -> str | None:
    """Читает текстовый файл, пробуя utf-8 и cp1251. Возвращает None при ошибке."""
    for enc in ("utf-8", "cp1251"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, OSError):
            continue
    return None


def find_matching_brace(text: str, open_pos: int) -> int:
    """
    Находит закрывающую } для { на позиции open_pos.
    Пропускает содержимое строк (&quot;...&quot;, \\"...\\", "...") и комментариев (// и /* */).
    """
    depth = 0
    i = open_pos
    length = len(text)

    while i < length:
        # Однострочный комментарий // — пропускаем до конца строки
        if text[i] == '/' and i + 1 < length and text[i + 1] == '/':
            while i < length and text[i] != '\n':
                i += 1
            continue

        # Многострочный комментарий /* ... */
        if text[i] == '/' and i + 1 < length and text[i + 1] == '*':
            i += 2
            while i + 1 < length:
                if text[i] == '*' and text[i + 1] == '/':
                    i += 2
                    break
                i += 1
            continue

        # Backslash-escaped quote: \" — пропускаем строку между ними
        if text[i] == '\\' and i + 1 < length and text[i + 1] == '"':
            i += 2  # пропускаем \"
            while i < length:
                if text[i] == '\\' and i + 1 < length and text[i + 1] == '"':
                    i += 2  # закрывающая \"
                    break
                i += 1
            continue

        # &quot; — XML escaped quote, пропускаем строку между ними
        if text[i:i+6] == '&quot;':
            i += 6
            while i < length:
                if text[i:i+6] == '&quot;':
                    i += 6
                    break
                i += 1
            continue

        # Обычная строка в кавычках
        if text[i] == '"':
            i += 1
            while i < length:
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
            i += 1
            continue

        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i

        i += 1

    return -1


CABINETS_FILE = SCRIPT_DIR / "cabinets.txt"                 # список шкафов


def load_active_cabinets() -> set[str] | None:
    """Читает cabinets.txt → set имён. None = обрабатывать все."""
    if not CABINETS_FILE.exists():
        return None
    names: set[str] = set()
    for line in CABINETS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    return names if names else None


def find_cabinet_dirs(objects_dir: Path) -> list[Path]:
    """Возвращает отсортированный список папок objects_<ШКАФ>/ (с учётом cabinets.txt)."""
    if not objects_dir.exists():
        return []
    active = load_active_cabinets()
    dirs = []
    for d in objects_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("objects_"):
            continue
        cab_name = d.name.replace("objects_", "", 1)
        if active is not None and cab_name not in active:
            continue
        dirs.append(d)
    return sorted(dirs)


def find_mnemo_dirs() -> list[Path]:
    """Возвращает отсортированный список папок шкафов в LCSMnemo/ (с учётом cabinets.txt)."""
    if not LCSMEMO_DIR.exists():
        return []
    active = load_active_cabinets()
    dirs = []
    for d in LCSMEMO_DIR.iterdir():
        if not d.is_dir():
            continue
        if active is not None and d.name not in active:
            continue
        dirs.append(d)
    return sorted(dirs)
