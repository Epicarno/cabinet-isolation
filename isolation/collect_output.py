"""
Сборка результатов пайплайна в деплой-папки по шкафам.

Для каждого шкафа создаёт папку с полной структурой путей,
готовую к копированию на целевую машину:

  output/<ШКАФ>/
    ventcontent/
      panels/
        objects/
          objects_<ШКАФ>/...        ← изолированные объекты
        vision/
          LCSMnemo/
            <ШКАФ>/...              ← изменённые мнемосхемы
      scripts/
        libs/
          objLogic/
            Ventcontent_<ШКАФ>.ctl  ← индивидуальный скрипт

Использование:
  python collect_output.py          — собрать все шкафы
  python collect_output.py --clean  — очистить output/ перед сборкой
"""

import sys
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parse_utils import (
    find_cabinet_dirs, SCRIPT_DIR, VENT_DIR,
    OBJECTS_DIR, LCSMEMO_DIR, CTL_DIR,
)

# Windows cp866/cp1251 ломает Unicode → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

OUTPUT_DIR = SCRIPT_DIR.parent / "output"

# Базовый путь — родитель ventcontent (т.е. Modules/)
BASE_DIR = VENT_DIR.parent


def collect_cabinet(cabinet_name: str) -> dict[str, int]:
    """Собирает все файлы одного шкафа в output/<ШКАФ>/."""
    stats = {"objects": 0, "mnemo": 0, "ctl": 0}
    cab_output = OUTPUT_DIR / cabinet_name

    # 1. Объекты: objects/objects_<ШКАФ>/ → output/<ШКАФ>/ventcontent/panels/objects/objects_<ШКАФ>/
    src_objects = OBJECTS_DIR / f"objects_{cabinet_name}"
    if src_objects.exists():
        dst_objects = cab_output / src_objects.relative_to(BASE_DIR)
        if dst_objects.exists():
            shutil.rmtree(dst_objects)
        shutil.copytree(src_objects, dst_objects)
        stats["objects"] = sum(1 for _ in dst_objects.rglob("*") if _.is_file())

    # 2. Мнемосхемы: vision/LCSMnemo/<ШКАФ>/ → output/<ШКАФ>/ventcontent/panels/vision/LCSMnemo/<ШКАФ>/
    src_mnemo = LCSMEMO_DIR / cabinet_name
    if src_mnemo.exists():
        dst_mnemo = cab_output / src_mnemo.relative_to(BASE_DIR)
        if dst_mnemo.exists():
            shutil.rmtree(dst_mnemo)
        shutil.copytree(src_mnemo, dst_mnemo)
        stats["mnemo"] = sum(1 for _ in dst_mnemo.rglob("*") if _.is_file())

    # 3. CTL: objLogic/Ventcontent_<ШКАФ>.ctl → output/<ШКАФ>/ventcontent/scripts/libs/objLogic/
    src_ctl = CTL_DIR / f"Ventcontent_{cabinet_name}.ctl"
    if src_ctl.exists():
        dst_ctl = cab_output / src_ctl.relative_to(BASE_DIR)
        dst_ctl.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_ctl, dst_ctl)
        stats["ctl"] = 1

    return stats


def main():
    clean = "--clean" in sys.argv

    if clean and OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        print(f"Очищено: {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Определяем шкафы из objects/objects_<ШКАФ>/
    cabinet_dirs = find_cabinet_dirs(OBJECTS_DIR)
    if not cabinet_dirs:
        print("Папки objects_<ШКАФ>/ не найдены.")
        return

    print(f"Сборка в {OUTPUT_DIR}")
    print(f"Шкафов: {len(cabinet_dirs)}\n")

    total_files = 0

    for cab_dir in cabinet_dirs:
        cabinet_name = cab_dir.name.replace("objects_", "", 1)
        stats = collect_cabinet(cabinet_name)

        files = stats["objects"] + stats["mnemo"] + stats["ctl"]
        total_files += files

        parts = []
        if stats["objects"]:
            parts.append(f"объектов: {stats['objects']}")
        if stats["mnemo"]:
            parts.append(f"мнемосхем: {stats['mnemo']}")
        if stats["ctl"]:
            parts.append(f"ctl: {stats['ctl']}")

        print(f"  [{cabinet_name}] {', '.join(parts)}")

    print(f"\nГотово: {total_files} файлов в {len(cabinet_dirs)} папках")
    print(f"Путь: {OUTPUT_DIR}")
    print(f"\nДеплой: скопируйте содержимое output/<ШКАФ>/ в корень проекта")


if __name__ == "__main__":
    main()
