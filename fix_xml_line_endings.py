"""
Конвертация CRLF → LF во всех XML файлах (objects/ и vision/).
"""

from pathlib import Path
from parse_utils import OBJECTS_DIR, VISION_DIR


def main():
    fixed = 0
    for scan_dir in [OBJECTS_DIR, VISION_DIR]:
        if not scan_dir.exists():
            continue
        for xml_file in scan_dir.rglob("*.xml"):
            raw = xml_file.read_bytes()
            if b'\r\n' in raw:
                xml_file.write_bytes(raw.replace(b'\r\n', b'\n'))
                fixed += 1

    print(f"Исправлено: {fixed} файлов")


if __name__ == "__main__":
    main()
