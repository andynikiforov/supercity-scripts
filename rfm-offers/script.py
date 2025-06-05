import json
import csv
import os
import sys
import argparse
from datetime import datetime
import textwrap
import re

class RfmOffersValidator:
    def __init__(self, requirements_file="requirements.csv", 
                 actions_file="actions.json", rfm_files=None, verbose=True, json_output=False):
        """
        Инициализация валидатора конфигурации RFM офферов.
        
        Args:
            requirements_file (str): Путь к CSV-файлу с требованиями
            actions_file (str): Путь к JSON-файлу с действиями
            rfm_files (dict): Словарь с путями к JSON-файлам RFM офферов (ключ - имя оффера)
            verbose (bool): Подробное логирование
            json_output (bool): Вывод в формате JSON (отключает текстовый вывод)
        """
        self.errors = []
        self.warnings = []
        self.info_logs = []
        self.verbose = verbose
        self.json_output = json_output
        
        # Цвета для вывода
        self.GREEN = "\033[92m"
        self.RED = "\033[91m"
        self.YELLOW = "\033[93m"
        self.BLUE = "\033[94m"
        self.MAGENTA = "\033[95m"
        self.CYAN = "\033[96m"
        self.BOLD = "\033[1m"
        self.UNDERLINE = "\033[4m"
        self.RESET = "\033[0m"
        
        # Статистика по проверкам
        self.stats = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "warning_checks": 0
        }
        
        # Прогресс по этапам
        self.current_phase = ""
        
        # Ошибки для сводной таблицы
        self.offer_errors = {}
        
        # Если rfm_files не указан, ищем по стандартному шаблону
        if rfm_files is None:
            rfm_files = {}
            for file in os.listdir():
                if file.startswith('rfm') and file.endswith('.json'):
                    offer_name = file.replace('.json', '')
                    rfm_files[offer_name] = file
        
        self.print_header("ВАЛИДАЦИЯ RFM ОФФЕРОВ")
        self.log_info(f"Файлы для проверки:")
        self.log_info(f"- Требования: {requirements_file}")
        self.log_info(f"- Экшены: {actions_file}")
        for offer_name, file_path in rfm_files.items():
            self.log_info(f"- {offer_name}: {file_path}")
        
        # Загрузка данных
        self.requirements = self._load_csv(requirements_file)
        self.actions = self._load_json(actions_file)
        self.rfm_configs = {}
        
        for offer_name, file_path in rfm_files.items():
            self.rfm_configs[offer_name] = self._load_json(file_path)
        
        # Создание словарей для быстрого поиска
        # Словарь для хранения требований по имени оффера
        self.requirements_by_offer = {}
        for req in self.requirements:
            if 'offer' in req and req['offer']:
                self.requirements_by_offer[req['offer']] = req

        # Словарь для хранения всех экшенов из actions.json
        self.actions_by_id = {}
        for action in self.actions:
            action_id = action.get('@id')
            if action_id:
                self.actions_by_id[int(action_id)] = action
        
        self.log_info(f"Загружено {len(self.requirements_by_offer)} записей из таблицы требований")
        self.log_info(f"Загружено {len(self.actions_by_id)} записей из файла экшенов")
        self.log_info(f"Загружено {len(self.rfm_configs)} RFM-конфигураций")
        print("")
        
    def _load_json(self, file_path):
        """Загрузка JSON-файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.log_info(f"✓ JSON-файл {file_path} успешно загружен")
                return data
        except Exception as e:
            error_msg = f"Ошибка при загрузке JSON-файла {file_path}: {str(e)}"
            self.log_error(error_msg)
            return {}
    
    def _load_csv(self, file_path):
        """Загрузка CSV-файла"""
        try:
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            self.log_info(f"✓ CSV-файл {file_path} успешно загружен")
            return data
        except Exception as e:
            error_msg = f"Ошибка при загрузке CSV-файла {file_path}: {str(e)}"
            self.log_error(error_msg)
            return []
    
    def print_header(self, text):
        """Печать заголовка с форматированием"""
        # Добавляем заголовок в лог
        log_entry = f"\n{'=' * 80}\n{text}\n{'=' * 80}"
        self.info_logs.append(log_entry)
        
        if self.json_output:
            return
            
        print("\n" + "=" * 80)
        print(f"{self.BOLD}{self.MAGENTA}{text}{self.RESET}")
        print("=" * 80)
    
    def log_info(self, message):
        """Логирование информационных сообщений"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[INFO] {timestamp} - {message}"
        self.info_logs.append(log_entry)
        if self.verbose and not self.json_output:
            print(f"{self.BLUE}[ИНФО]{self.RESET} {message}")
            
    def log_check(self, offer_name, check_name, result, expected=None, actual=None, details=None, check_tag=None):
        """Логирование результата проверки"""
        self.stats["total_checks"] += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Формируем дополнительную информацию для лога
        extra_info = ""
        if expected is not None and actual is not None:
            extra_info = f" (ожидалось: {expected}, фактически: {actual})"
        
        if result:
            self.stats["passed_checks"] += 1
            status = f"{self.GREEN}✓ УСПЕХ{self.RESET}"
            log_msg = f"[CHECK:OK] {timestamp} - {offer_name}: {check_name}{extra_info}"
        else:
            self.stats["failed_checks"] += 1
            status = f"{self.RED}✗ ОШИБКА{self.RESET}"
            log_msg = f"[CHECK:FAIL] {timestamp} - {offer_name}: {check_name}{extra_info}"
            
            # Добавляем ошибку в список ошибок для этого offer_name
            if offer_name not in self.offer_errors:
                self.offer_errors[offer_name] = []
            
            error_details = {
                "check": check_name,
                "expected": expected,
                "actual": actual,
                "details": details,
                "tag": check_tag
            }
            self.offer_errors[offer_name].append(error_details)
            
            # Добавляем в общий список ошибок
            error_msg = f"{offer_name}: {check_name}"
            if expected is not None and actual is not None:
                error_msg += f" (ожидалось: {expected}, получено: {actual})"
            if details:
                error_msg += f" - {details}"
            self.errors.append(error_msg)
        
        self.info_logs.append(log_msg)
        
        if self.verbose and not self.json_output:
            print(f"{status} {offer_name}: {check_name}{extra_info}")
            if details and not result:
                print(f"  {details}")
    
    def log_warning(self, message, offer_name=None):
        """Логирование предупреждений"""
        self.stats["warning_checks"] += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if offer_name is not None:
            log_msg = f"[WARNING] {timestamp} - {offer_name}: {message}"
            display_msg = f"{self.YELLOW}[ВНИМАНИЕ]{self.RESET} {offer_name}: {message}"
            
            # Добавляем предупреждение в список для этого offer_name
            if offer_name not in self.offer_errors:
                self.offer_errors[offer_name] = []
            
            self.offer_errors[offer_name].append({
                "check": "warning",
                "expected": None,
                "actual": None,
                "details": message,
                "tag": "WARNING"
            })
        else:
            log_msg = f"[WARNING] {timestamp} - {message}"
            display_msg = f"{self.YELLOW}[ВНИМАНИЕ]{self.RESET} {message}"
        
        self.info_logs.append(log_msg)
        self.warnings.append(message)
        
        if self.verbose and not self.json_output:
            print(display_msg)
    
    def log_error(self, message, offer_name=None):
        """Логирование ошибок"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if offer_name is not None:
            log_msg = f"[ERROR] {timestamp} - {offer_name}: {message}"
            display_msg = f"{self.RED}[ОШИБКА]{self.RESET} {offer_name}: {message}"
            
            # Добавляем ошибку в список для этого offer_name
            if offer_name not in self.offer_errors:
                self.offer_errors[offer_name] = []
            
            self.offer_errors[offer_name].append({
                "check": "error",
                "expected": None,
                "actual": None,
                "details": message,
                "tag": "ERROR"
            })
        else:
            log_msg = f"[ERROR] {timestamp} - {message}"
            display_msg = f"{self.RED}[ОШИБКА]{self.RESET} {message}"
        
        self.info_logs.append(log_msg)
        self.errors.append(message)
        
        if self.verbose and not self.json_output:
            print(display_msg)
    
    def start_phase(self, phase_name):
        """Начало новой фазы проверки"""
        self.current_phase = phase_name
        self.print_header(f"ФАЗА: {phase_name}")
    
    def validate_all(self):
        """Запуск всех проверок"""
        # Фаза 1: Проверка наличия Action ID из требований в actions.json
        self.validate_action_ids_in_actions()
        
        # Фаза 2: Проверка наград и необходимых ресурсов в экшенах
        self.validate_action_rewards_and_resources()
        
        # Фаза 3: Проверка соответствия RFM файлов требованиям
        self.validate_rfm_files()
        
        # Вывод итогового отчёта
        self.print_summary()
        
    def validate_action_ids_in_actions(self):
        """Проверка наличия указанных Action ID из требований в actions.json"""
        self.start_phase("ПРОВЕРКА НАЛИЧИЯ ACTION ID В ACTIONS.JSON")
        
        for offer_name, req in self.requirements_by_offer.items():
            action_id = int(req.get('action', 0))
            exists = action_id in self.actions_by_id
            
            self.log_check(
                offer_name, 
                f"Наличие Action ID {action_id} в actions.json",
                exists,
                "Присутствует",
                "Присутствует" if exists else "Отсутствует",
                None,
                "ACTION_EXISTS"
            )
            
    def validate_action_rewards_and_resources(self):
        """Проверка наград и необходимых ресурсов в экшенах"""
        self.start_phase("ПРОВЕРКА НАГРАД И НЕОБХОДИМЫХ РЕСУРСОВ В ЭКШЕНАХ")
        
        for offer_name, req in self.requirements_by_offer.items():
            action_id = int(req.get('action', 0))
            
            # Пропускаем проверку, если экшена нет в actions.json
            if action_id not in self.actions_by_id:
                self.log_warning(f"Пропуск проверки наград для отсутствующего экшена {action_id}", offer_name)
                continue
            
            action = self.actions_by_id[action_id]
            
            # 1. Проверка наград (количество очков)
            awards = action.get('awards', [])
            expected_award = int(req.get('award', 0))
            expected_tech_item = int(req.get('techitem', 0))
            
            # Ищем награду типа "item" с itemId, соответствующим очкам (17909 обычно)
            award_found = False
            actual_award = 0
            
            for award in awards:
                if award.get('type') == 'item' and award.get('itemId') == 17909:  # ID для очков
                    award_found = True
                    actual_award = award.get('count', 0)
                    break
            
            self.log_check(
                offer_name,
                f"Количество очков в награде экшена {action_id}",
                award_found and actual_award == expected_award,
                expected_award,
                actual_award if award_found else "Не найдено",
                None,
                "AWARD_POINTS_CHECK"
            )
            
            # 2. Проверка необходимых ресурсов (цена)
            need_resources = action.get('needResources', [])
            expected_price = float(req.get('price', 0))
            actual_price = 0
            price_found = False
            
            for resource in need_resources:
                if resource.get('type') == 'cash':
                    price_found = True
                    actual_price = float(resource.get('count', 0))
                    break
            
            self.log_check(
                offer_name,
                f"Цена в needResources экшена {action_id}",
                price_found and abs(actual_price - expected_price) < 0.001,
                expected_price,
                actual_price if price_found else "Не найдено",
                None,
                "PRICE_CHECK"
            )
    
    def _normalize_date_format(self, date_str):
        """Нормализация формата даты для сравнения"""
        if not date_str:
            return ""
        
        # Заменяем формат без ведущего нуля (7:00:00) на формат с ведущим нулем (07:00:00)
        hour_pattern = r'(\d{4}-\d{2}-\d{2}) (\d):(\d{2}):(\d{2})'
        match = re.match(hour_pattern, date_str)
        if match:
            date_part, hour, minute, second = match.groups()
            return f"{date_part} {hour.zfill(2)}:{minute}:{second}"
        
        return date_str
        
    def _find_hasItems_in_dict(self, d):
        """Рекурсивный поиск hasItems в словаре"""
        if not isinstance(d, dict):
            return None
            
        if "hasItems" in d:
            return d["hasItems"]
            
        for k, v in d.items():
            if isinstance(v, dict):
                result = self._find_hasItems_in_dict(v)
                if result:
                    return result
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        result = self._find_hasItems_in_dict(item)
                        if result:
                            return result
        
        return None

    def validate_rfm_files(self):
        """Проверка соответствия RFM файлов требованиям"""
        self.start_phase("ПРОВЕРКА СООТВЕТСТВИЯ RFM ФАЙЛОВ ТРЕБОВАНИЯМ")
        
        for offer_name, req in self.requirements_by_offer.items():
            # Проверяем, есть ли конфигурация для этого оффера
            if offer_name not in self.rfm_configs:
                self.log_warning(f"Файл конфигурации не найден для оффера {offer_name}", offer_name)
                continue
            
            rfm_config = self.rfm_configs[offer_name]
            
            # 1. Проверка Award ID в массиве awards
            expected_action_id = int(req.get('action', 0))
            awards_array = rfm_config.get('awards', [])
            action_in_awards = expected_action_id in awards_array
            
            self.log_check(
                offer_name,
                "Наличие Action ID в массиве awards",
                action_in_awards,
                expected_action_id,
                awards_array,
                None,
                "ACTION_IN_AWARDS"
            )
            
            # 2. Проверка дат начала и окончания с нормализацией форматов
            expected_start = self._normalize_date_format(req.get('start', ''))
            expected_end = self._normalize_date_format(req.get('end', ''))
            actual_start = self._normalize_date_format(rfm_config.get('from', ''))
            actual_end = self._normalize_date_format(rfm_config.get('to', ''))
            
            self.log_check(
                offer_name,
                "Дата начала акции",
                expected_start == actual_start,
                expected_start,
                actual_start,
                None,
                "START_DATE_CHECK"
            )
            
            self.log_check(
                offer_name,
                "Дата окончания акции",
                expected_end == actual_end,
                expected_end,
                actual_end,
                None,
                "END_DATE_CHECK"
            )
            
            # 3. Проверка параметров в controlSettings
            control_settings = rfm_config.get('parameters', {}).get('controlSettings', [])
            
            # 3.1 Проверка скидки
            expected_discount = f"-{req.get('discount', '')}%"
            discount_found = False
            actual_discount = ""
            
            for setting in control_settings:
                if setting.get('displayObject', '').endswith('/discount'):
                    discount_found = True
                    actual_discount = setting.get('textKeyFit', '')
                    break
            
            self.log_check(
                offer_name,
                "Скидка в controlSettings",
                discount_found and expected_discount == actual_discount,
                expected_discount,
                actual_discount if discount_found else "Не найдено",
                None,
                "DISCOUNT_CHECK"
            )
            
            # 3.2 Проверка количества очков
            expected_award_text = f"x{req.get('award', '')}"
            count_found = False
            actual_count = ""
            
            for setting in control_settings:
                if setting.get('displayObject', '').endswith('/count'):
                    count_found = True
                    actual_count = setting.get('textKeyFit', '')
                    break
            
            self.log_check(
                offer_name,
                "Количество очков в controlSettings",
                count_found and expected_award_text == actual_count,
                expected_award_text,
                actual_count if count_found else "Не найдено",
                None,
                "COUNT_CHECK"
            )
            
            # 3.3 Проверка старой цены
            expected_old_price = req.get('old_price', '')
            price_found = False
            actual_old_price = ""
            
            for setting in control_settings:
                if setting.get('displayObject', '').endswith('/txtCost'):
                    price_found = True
                    actual_old_price = setting.get('textKeyFit', '')
                    break
            
            self.log_check(
                offer_name,
                "Старая цена в controlSettings",
                price_found and str(expected_old_price) == str(actual_old_price),
                expected_old_price,
                actual_old_price if price_found else "Не найдено",
                None,
                "OLD_PRICE_CHECK"
            )
            
            # 4. Проверка сегментов
            expected_segments = req.get('segment', '').split(',')
            expected_segments = [segment.strip() for segment in expected_segments if segment.strip()]
            
            settings_by_conditions = rfm_config.get('parameters', {}).get('settingsByConditions', [])
            segment_condition_found = False
            actual_segments = []
            
            for condition_setting in settings_by_conditions:
                conditions = condition_setting.get('conditions', {})
                if 'isNotInOneOfRFM30Segments' in conditions:
                    segment_condition_found = True
                    actual_segments = conditions['isNotInOneOfRFM30Segments'].split(',')
                    actual_segments = [segment.strip() for segment in actual_segments if segment.strip()]
                    break
            
            # Сортируем для корректного сравнения
            expected_segments.sort()
            actual_segments.sort()
            
            self.log_check(
                offer_name,
                "Сегменты в settingsByConditions",
                segment_condition_found and expected_segments == actual_segments,
                ",".join(expected_segments),
                ",".join(actual_segments) if segment_condition_found else "Не найдено",
                None,
                "SEGMENTS_CHECK"
            )
            
            # 5. ПРОВЕРКА ТЕХАЙТЕМА: 
            # - ID техайтема извлекается из названия колонки "techitem(17908)" -> 17908
            # - В колонке указано ожидаемое количество техайтема
            
            # Ищем колонку с техайтемом в формате "techitem(ID)"
            techitem_column = None
            techitem_id = None
            
            for column_name in req.keys():
                if column_name.startswith('techitem(') and column_name.endswith(')'):
                    techitem_column = column_name
                    # Извлекаем ID из названия колонки
                    match = re.search(r'techitem\((\d+)\)', column_name)
                    if match:
                        techitem_id = int(match.group(1))
                    break
            
            if techitem_column and techitem_id:
                # Получаем требуемое количество техайтема из колонки
                techitem_count_str = req.get(techitem_column, '')
                
                # Очищаем count от возможных символов процентов
                if techitem_count_str:
                    techitem_count_str = techitem_count_str.rstrip('%')
                    
                    try:
                        expected_count = int(techitem_count_str)
                        
                        # Ищем техайтем в settingsByConditions
                        techitem_found = False
                        actual_count = None
                        actual_id = None
                        
                        for condition_setting in settings_by_conditions:
                            conditions = condition_setting.get('conditions', {})
                            if 'hasItems' in conditions:
                                has_items = conditions['hasItems']
                                # Проверяем все техайтемы, найденные в hasItems
                                for item in has_items:
                                    if 'itemID' in item:
                                        if item.get('itemID') == techitem_id:
                                            techitem_found = True
                                            actual_count = item.get('count')
                                            actual_id = item.get('itemID')
                                            break
                                        else:
                                            # Если не совпадает с ожидаемым ID, запоминаем для отчета
                                            actual_id = item.get('itemID')
                                if techitem_found:
                                    break
                        
                        # Проверка наличия техайтема с правильным ID
                        self.log_check(
                            offer_name,
                            f"Правильный ID техайтема ({techitem_id}) в hasItems",
                            techitem_found,
                            techitem_id,
                            actual_id if actual_id is not None else "Не найден",
                            None,
                            "TECHITEM_ID_CHECK"
                        )
                        
                        # Проверка количества техайтема, только если найден правильный ID
                        if techitem_found and actual_count is not None:
                            self.log_check(
                                offer_name,
                                f"Количество техайтема (ID {techitem_id}) в hasItems",
                                actual_count == expected_count,
                                expected_count,
                                actual_count,
                                None,
                                "TECHITEM_COUNT_CHECK"
                            )
                        elif techitem_found:
                            self.log_warning(f"Техайтем {techitem_id} найден в hasItems, но без указания количества", offer_name)
                        
                    except ValueError:
                        self.log_warning(f"Некорректный формат количества техайтема: {techitem_count_str}", offer_name)
            else:
                self.log_info(f"Колонка с техайтемом не найдена в требованиях для оффера {offer_name}")
    
    def print_summary(self):
        """Печать итогового отчета"""
        self.print_header("ИТОГОВЫЙ ОТЧЕТ")
        
        total_checks = self.stats["total_checks"]
        passed = self.stats["passed_checks"]
        failed = self.stats["failed_checks"]
        warnings = self.stats["warning_checks"]
        
        success_rate = (passed / total_checks * 100) if total_checks > 0 else 0
        
        summary = [
            f"Всего проверок: {total_checks}",
            f"Успешных проверок: {passed} ({success_rate:.1f}%)",
            f"Неудачных проверок: {failed}",
            f"Предупреждений: {warnings}"
        ]
        
        for line in summary:
            self.log_info(line)
            
        if failed > 0:
            self.print_header("СПИСОК ОШИБОК")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
    
    def save_report_to_csv(self, output_file="validation_report.csv"):
        """Сохранение отчета в CSV-файл"""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Оффер", "Проверка", "Результат", "Ожидаемое", "Фактическое", "Детали"])
                
                for offer_name, errors in self.offer_errors.items():
                    for error in errors:
                        writer.writerow([
                            offer_name,
                            error.get("check", ""),
                            "ОШИБКА" if error.get("tag") != "WARNING" else "ПРЕДУПРЕЖДЕНИЕ",
                            error.get("expected", ""),
                            error.get("actual", ""),
                            error.get("details", "")
                        ])
                        
            self.log_info(f"Отчет сохранен в файл: {output_file}")
        except Exception as e:
            self.log_error(f"Ошибка при сохранении отчета: {str(e)}")
    
    def save_detailed_log(self, output_file="validation_detailed.log"):
        """Сохранение подробного лога в файл"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in self.info_logs:
                    # Удаление ANSI-кодов цветов
                    clean_line = line
                    for color_code in [self.GREEN, self.RED, self.YELLOW, self.BLUE, 
                                      self.MAGENTA, self.CYAN, self.BOLD, self.UNDERLINE, self.RESET]:
                        clean_line = clean_line.replace(color_code, "")
                    f.write(clean_line + "\n")
            self.log_info(f"Подробный лог сохранен в файл: {output_file}")
        except Exception as e:
            self.log_error(f"Ошибка при сохранении лога: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Валидатор RFM офферов')
    parser.add_argument('--requirements', default="requirements.csv", help='Путь к файлу requirements.csv')
    parser.add_argument('--actions', default="actions.json", help='Путь к файлу actions.json')
    parser.add_argument('--rfm-files', action='append', nargs=2, metavar=('OFFER_NAME', 'FILE_PATH'), 
                      help='Пары имя_оффера путь_к_файлу для RFM конфигураций')
    parser.add_argument('--report', default="validation_report.csv", help='Путь к файлу отчета')
    parser.add_argument('--log', default="validation_detailed.log", help='Путь к файлу лога')
    parser.add_argument('--quiet', action='store_true', help='Минимальный вывод в консоль')
    parser.add_argument('--json', action='store_true', help='Вывод в формате JSON')
    
    args = parser.parse_args()
    
    # Преобразуем список пар в словарь
    rfm_files = None
    if args.rfm_files:
        rfm_files = {offer_name: file_path for offer_name, file_path in args.rfm_files}
    
    validator = RfmOffersValidator(
        requirements_file=args.requirements,
        actions_file=args.actions,
        rfm_files=rfm_files,
        verbose=not args.quiet,
        json_output=args.json
    )
    
    validator.validate_all()
    validator.save_report_to_csv(args.report)
    validator.save_detailed_log(args.log)

if __name__ == "__main__":
    main() 