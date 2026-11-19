# TP_course_project

[![CI](https://github.com/IvanTsiak/TP_course_project/actions/workflows/ci.yml/badge.svg)](https://github.com/IvanTsiak/TP_course_project/actions/workflows/ci.yml)

Посилання на відео: https://drive.google.com/file/d/1FxFP-oowfiiwoQoQjIEn-4umCM-S_XdZ/view?usp=sharing

Виконані завдання: CORE-01 (0.5 б), CORE-02 (1.5 б), CORE-03 (2 б), CORE-04 (1 б), VIS-01 (1.5 б), REL-01 (0.5 б), REL-02 (0.5 б), REL-03 (0.5 б)  
Всього: 8 б

## Встановлення

### Із PyPI 
```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install TP-course-project
```

## Запуск та приклади

1. **Виконання програми з початковим станом ($X^Y$):**
```bash
sipl examples/valid/power.sipl --state '{\"X\": 2, \"Y\": 3}'
```

2. **Отримання лише журналу подій у JSON:**
```bash
sipl examples/valid/fibonacci.sipl --state '{"N": 8}' --trace-only
```

3. **Візуалізація дерева синтаксичного виводу (`text`, `json`, `dot`, `svg`):**
```bash
sipl examples/valid/power.sipl --parse-tree text
sipl examples/valid/power.sipl --parse-tree svg > parse_tree.svg
```

4. **Перевірка діагностики помилок:**
```bash
sipl examples/invalid/missing_else.sipl
```

## Тестування

```bash
pytest --cov=sipl --cov-report=term-missing
```