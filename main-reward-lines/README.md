# Валидатор наград сезонного пропуска

Скрипт для проверки корректности настройки наград в конфигурации сезонного пропуска.

## Назначение

Данный скрипт предназначен для автоматизированной проверки конфигурации наград сезонного пропуска, включая:

1. Проверку наличия всех требуемых экшенов в promo.json и actions.json
2. Проверку соответствия содержимого экшенов требованиям из таблицы requirements.csv
3. Проверку настроек needResources и наград в каждом экшене
4. Проверку наличия и корректности настройки needAction для платных наград

## Требования

Для работы скрипта необходимы:

- Python 3.6 или выше
- Следующие файлы в папке запуска:
  - `promo.json` - файл с конфигурацией промо акции
  - `requirements.csv` - CSV-файл с требованиями к экшенам
  - `actions.json` - файл с описанием экшенов

## Структура CSV-файла с требованиями

`requirements.csv` должен содержать следующие колонки:
- `№` - порядковый номер строки
- `action_free` - ID экшена бесплатной награды
- `needResources (17886)` - количество необходимых ресурсов
- `Бесплатная награда` - описание бесплатной награды
- `award_1_type` - тип бесплатной награды (item, buff, cash, season_currency)
- `award_1_id` - ID бесплатной награды
- `award_1_qty` - количество единиц бесплатной награды
- `action_paid` - ID экшена платной награды
- `Платная награда` - описание платной награды
- `award_2_type` - тип платной награды (item, buff, cash, season_currency)
- `award_2_id` - ID платной награды
- `award_2_qty` - количество единиц платной награды

## Запуск

### Базовый запуск

```bash
python script.py
```

Запуск с этой командой будет использовать файлы `promo.json`, `requirements.csv` и `actions.json` из текущей директории.

### Запуск с указанием путей к файлам

```bash
python script.py --promo путь/к/promo.json --requirements путь/к/requirements.csv --actions путь/к/actions.json
```

### Дополнительные параметры

```bash
python script.py --verbose --report отчет.csv --log подробный_лог.log
```

## Параметры командной строки

- `--promo` - путь к JSON-файлу с промо-акцией (по умолчанию: `promo.json`)
- `--requirements` - путь к CSV-файлу с требованиями (по умолчанию: `requirements.csv`)
- `--actions` - путь к JSON-файлу с действиями (по умолчанию: `actions.json`)
- `--verbose` - включение подробного логирования
- `--json-output` - вывод в формате JSON (отключает текстовый вывод)
- `--report` - имя файла для сохранения отчета (по умолчанию: `validation_report.csv`)
- `--log` - имя файла для сохранения детального лога (по умолчанию: `validation_detailed.log`)

## Интерпретация результатов

Скрипт выполняет две фазы проверки:

### Фаза 1: Проверка наличия экшенов
- Проверяет, что все экшены из таблицы требований есть в промо
- Проверяет, что все экшены из таблицы требований есть в файле экшенов
- Проверяет, что все экшены из промо есть в таблице требований

### Фаза 2: Проверка содержимого экшенов
- Проверяет соответствие needResources значениям из таблицы
- Проверяет наличие и тип наград в экшенах
- Проверяет соответствие количества наград значениям из таблицы
- Для платных наград проверяет наличие needAction и ID сезонного пропуска

## Выходные данные

После завершения проверки скрипт создает:

1. `validation_report.csv` - сводный отчет по всем обнаруженным ошибкам
2. `validation_detailed.log` - подробный лог выполнения проверок

Отчет в формате CSV содержит следующие колонки:
- Action ID - идентификатор экшена
- Проверка - название проверки
- Результат - результат проверки (Ошибка/Предупреждение)
- Ожидаемое - ожидаемое значение
- Фактическое - фактическое значение
- Детали - детали ошибки

## Примеры использования

### Базовая проверка текущей конфигурации

```bash
python script.py --verbose
```

### Проверка с сохранением результатов в специальные файлы

```bash
python script.py --verbose --report результаты.csv --log подробный_лог.txt
```

### Проверка файлов, расположенных в другой директории

```bash
python script.py --promo /путь/к/promo.json --requirements /путь/к/requirements.csv --actions /путь/к/actions.json
```

## Возможные ошибки и их решение

1. **Ошибки наличия экшенов в файлах**: 
   - Проверьте, что все экшены из таблицы требований присутствуют в файле промо и файле экшенов
   - Проверьте, что идентификаторы (ID) экшенов совпадают

2. **Ошибки соответствия needResources**:
   - Проверьте, что значения в колонке "needResources (17886)" соответствуют значениям в экшенах

3. **Ошибки наград**:
   - Проверьте, что типы наград соответствуют указанным в таблице
   - Проверьте, что ID наград совпадают
   - Проверьте, что количество наград совпадает

4. **Ошибки needAction для платных наград**:
   - Проверьте наличие поля needAction в экшенах платных наград
   - Проверьте, что needAction содержит ID battlepassAction или один из seasonPassActions 