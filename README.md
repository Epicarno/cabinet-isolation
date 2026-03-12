# Изоляция шкафов

## Структура проекта

```
Modules/
├── scripts/                        ← Python-скрипты (этот репозиторий)
│   ├── cabinets.txt                ← список шкафов для обработки (фильтр)
│   │
│   ├── isolation/                  ← Пайплайн изоляции шкафов
│   │   ├── run_pipeline.py         ← раннер пайплайна
│   │   ├── run_pipeline.bat        ← обёртка для CMD (Windows)
│   │   ├── parse_utils.py          ← общие утилиты и пути проекта
│   │   ├── report_utils.py         ← запись отчётов (--append режим)
│   │   ├── Denostration_Ventcontent.ctl ← Demo-библиотека (встроена)
│   │   ├── process_mnemo.py        ← шаг 1: копирование объектов
│   │   ├── fix_cross_refs.py       ← шаг 2: перекрёстные ссылки
│   │   ├── cleanup_orphans.py      ← шаг 3: удаление сирот
│   │   ├── clean_commented_refs.py ← шаг 4: закомментированные ссылки
│   │   ├── validate_refs.py        ← шаг 5: валидация ссылок
│   │   ├── split_ctl.py            ← шаг 6: разбиение .ctl
│   │   ├── replace_scripts.py      ← шаг 7: замена #uses
│   │   ├── scan_problems.py        ← шаг 8: анализ проблем
│   │   ├── check_other_scripts.py  ← шаг 9: чужие скрипты → JSON
│   │   ├── cleanup_classes.py      ← шаг 10: удаление if-блоков
│   │   └── collect_output.py       ← шаг 11: сборка output/
│
├── ventcontent/                    ← проект WinCC OA
│   ├── panels/
│   │   ├── vision/
│   │   │   └── LCSMnemo/
│   │   │       ├── SHD_03_1/       ← папка шкафа
│   │   │       │   ├── *.xml       ← мнемосхемы
│   │   │       │   └── *.csv       ← описания объектов (колонки: refName, dpName, System, ObjctType, struct, CommonDP)
│   │   │       ├── SHD_05_1/
│   │   │       └── ...             ← ~24 шкафа
│   │   └── objects/
│   │       ├── PV/                 ← шаблоны объектов
│   │       ├── objects_SHD_03_1/   ← изолированные объекты (генерируются)
│   │       └── ...
│   └── scripts/
│       └── libs/
│           └── objLogic/
│               ├── PNR_Ventcontent.ctl        ← оригинал (59 классов)
│               ├── Ventcontent_SHD_03_1.ctl   ← генерируются split_ctl.py
│               └── ...
│
├── old_mnemo/                      ← бэкапы оригинальных мнемосхем
│   ├── SHD_03_1/                   ← копии XML до модификации
│   └── ...
│
├── output/                         ← деплой-папки (генерируются шаг 10)
│   ├── SHD_03_1/
│   │   └── ventcontent/            ← готово к копированию на целевую машину
│   │       ├── panels/objects/objects_SHD_03_1/...
│   │       ├── panels/vision/LCSMnemo/SHD_03_1/...
│   │       └── scripts/libs/objLogic/Ventcontent_SHD_03_1.ctl
│   └── ...
│
├── reports/                        ← отчёты (генерируются автоматически)
│   ├── split_ctl_report.txt
│   └── other_scripts.json          ← JSON обмен между скриптами
```

## Пайплайн (11 шагов)

### Выбор шкафов

Файл `cabinets.txt` управляет тем, какие шкафы обрабатываются. По одному на строку, `#` — комментарий:

```
# Раскомментируйте нужные шкафы:
SHD_03_1
SHD_05_1
# SHD_10_1     ← пропущен
```

Если файл пустой, все строки закомментированы или файл отсутствует — обрабатываются **все** шкафы.

### Запуск

Основной раннер — `run_pipeline.py` (Python). Файл `run_pipeline.bat` — тонкая обёртка для CMD.

**Важно: репозиторий клонируется как `Modules/scripts/`**, а не внутрь `ventcontent/`:

```bash
cd /path/to/Modules
git clone https://github.com/Epicarno/cabinet-isolation scripts
```

Результат:
```
Modules/
├── scripts/          ← этот репозиторий
├── ventcontent/      ← проект WinCC OA (отдельный репо)
├── reports/          ← генерируются автоматически
└── output/           ← генерируются автоматически
```

```bash
# Windows (CMD):
cd scripts\isolation
run_pipeline.bat                    # полный запуск
run_pipeline.bat --from 5           # продолжить с шага 5

# Windows / Linux / macOS (Python, рекомендуется):
cd scripts
python3 isolation/run_pipeline.py              # полный запуск
python3 isolation/run_pipeline.py --from 5     # продолжить с шага 5
python3 isolation/run_pipeline.py --only 8     # только шаг 8
python3 isolation/run_pipeline.py --append     # дописывать в отчёты
```

### Шаги

| # | Скрипт | Фаза | Описание |
|---|--------|------|----------|
| 1 | `process_mnemo.py` | Подготовка | Для каждого шкафа копирует `objects/PV/` → `objects/objects_<ШКАФ>/PV/` через `shutil.copytree`. Бэкапит оригиналы мнемосхем в `old_mnemo/<ШКАФ>/`. В XML мнемосхем заменяет `objects/PV/...` → `objects/objects_<ШКАФ>/PV/...`. Также обрабатывает `pathFS`-ссылки без `.xml` (формат `/objects/PV/FPs/...` → `/objects/objects_<ШКАФ>/PV/FPs/...`) |
| 2 | `fix_cross_refs.py` | Подготовка | Итеративно находит и исправляет перекрёстные ссылки внутри объектов: `objects/PV/...` → `objects/objects_<ШКАФ>/PV/...`. Копирует недостающие объекты из общей папки |
| 3 | `cleanup_orphans.py` | Подготовка | Удаляет файлы в `objects_<ШКАФ>/`, на которые никто не ссылается (артефакты `copytree` — объекты от других шкафов). Перед поиском ссылок вычищает комментарии (`//`, `/* */`) через `strip_comments` — закомментированные ссылки не считаются. Распознаёт `pathFS`-ссылки без `.xml`. Аргумент `2` = удалять, иначе только отчёт |
| 4 | `clean_commented_refs.py` | Подготовка | Находит файлы, на которые ссылаются **только** из закомментированного кода (`//`, `/* */`). Удаляет такие файлы и вычищает закомментированные строки-ссылки. `--apply` = удалять, по умолчанию dry-run |
| 5 | `validate_refs.py` | Проверка | Проверяет что все ссылки `objects/...xml` в XML указывают на реально существующие файлы. Игнорирует ссылки внутри комментариев (`//`, `/* */`) через `strip_comments`. Распознаёт `pathFS`-ссылки без `.xml` |
| 6 | `split_ctl.py` | Генерация | Парсит `PNR_Ventcontent.ctl` на секции (uses, классы, setValueLib, global, mapping). Для каждого шкафа читает CSV → определяет struct → находит нужные классы (+ родители + через маппинг) → собирает минимальный `Ventcontent_<ШКАФ>.ctl` |
| 7 | `replace_scripts.py` | Генерация | В XML объектах заменяет `#uses "objLogic/PNR_Ventcontent"` и `Denostration_Ventcontent` на `Ventcontent_<ШКАФ>.ctl`. Нормализует формат, удаляет дубли `#uses` |
| 8 | `scan_problems.py` | 📊 Анализ | Ищет проблемные паттерны: комментарии с `&quot;` (ломают парсинг), `else if` + struct, `switch` + struct |
| 9 | `check_other_scripts.py` | 📊 Анализ | Для каждого XML находит `#uses` → загружает классы из сторонних скриптов. Если struct-класс не из Ventcontent, но есть в другом скрипте — помечает как защищённый. Сохраняет `reports/other_scripts.json` |
| 10 | `cleanup_classes.py` | 🔧 Очистка | Загружает `other_scripts.json`, объединяет защищённые классы с доступными из `Ventcontent_<ШКАФ>.ctl`. Удаляет if-блоки для классов, которых нет ни там, ни там |
| 11 | `collect_output.py` | 📦 Сборка | Собирает результаты в `output/<ШКАФ>/ventcontent/...` — готовые папки с полной структурой путей для деплоя на целевую машину |
