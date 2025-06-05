import json
import csv
import os
import sys
import argparse
from datetime import datetime
import textwrap
import re

class EndNewsDoublePointsValidator:
    def __init__(self, end_news_promo_file="end-news-promo.json", double_points_promo_file="double-points-promo.json", 
                 promo_file="promo.json", requirements_file="requirements.csv", verbose=True, json_output=False):
        """
        Инициализация валидатора конфигурации окон напоминаний.
        
        Args:
            end_news_promo_file (str): Путь к JSON-файлу с промо окна завершения акции
            double_points_promo_file (str): Путь к JSON-файлу с промо двойных очков
            promo_file (str): Путь к основному JSON-файлу с промо-акцией
            requirements_file (str): Путь к CSV-файлу с требованиями
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
        self.config_errors = {}
        
        self.print_header("ВАЛИДАЦИЯ ОКОН НАПОМИНАНИЙ И ДВОЙНЫХ ОЧКОВ")
        self.log_info(f"Файлы для проверки:")
        self.log_info(f"- Промо окна завершения: {end_news_promo_file}")
        self.log_info(f"- Промо двойных очков: {double_points_promo_file}")
        self.log_info(f"- Основное промо: {promo_file}")
        self.log_info(f"- Требования: {requirements_file}")
        
        # Загрузка данных
        self.end_news_promo = self._load_json(end_news_promo_file)
        self.double_points_promo = self._load_json(double_points_promo_file)
        self.promo = self._load_json(promo_file)
        self.requirements = self._load_csv(requirements_file)
        
        # Обработка требований в более удобный формат
        self.requirements_by_alias = {}
        for req in self.requirements:
            if 'alias' in req and req['alias']:
                self.requirements_by_alias[req['alias']] = req
        
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
            
    def log_check(self, check_id, check_name, result, expected=None, actual=None, details=None):
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
            log_msg = f"[CHECK:OK] {timestamp} - {check_name}{extra_info}"
        else:
            self.stats["failed_checks"] += 1
            status = f"{self.RED}✗ ОШИБКА{self.RESET}"
            log_msg = f"[CHECK:FAIL] {timestamp} - {check_name}{extra_info}"
            
            # Добавляем ошибку в список ошибок
            if check_id not in self.config_errors:
                self.config_errors[check_id] = []
            
            error_details = {
                "check": check_name,
                "expected": expected,
                "actual": actual,
                "details": details
            }
            self.config_errors[check_id].append(error_details)
            
            # Добавляем в общий список ошибок
            error_msg = check_name
            if expected is not None and actual is not None:
                error_msg += f" (ожидалось: {expected}, получено: {actual})"
            if details:
                error_msg += f" - {details}"
            self.errors.append(error_msg)
        
        self.info_logs.append(log_msg)
        
        if self.verbose and not self.json_output:
            print(f"{status} {check_name}{extra_info}")
            
    def log_warning(self, message, check_id=None):
        """Логирование предупреждений"""
        self.stats["warning_checks"] += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[WARNING] {timestamp} - {message}"
        self.info_logs.append(log_entry)
        self.warnings.append(message)
        
        if self.verbose and not self.json_output:
            print(f"{self.YELLOW}[ПРЕДУПРЕЖДЕНИЕ]{self.RESET} {message}")
    
    def log_error(self, message, check_id=None):
        """Логирование ошибок"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[ERROR] {timestamp} - {message}"
        self.info_logs.append(log_entry)
        self.errors.append(message)
        
        if self.verbose and not self.json_output:
            print(f"{self.RED}[ОШИБКА]{self.RESET} {message}")
            
    def start_phase(self, phase_name):
        """Начало новой фазы проверки"""
        self.current_phase = phase_name
        self.print_header(f"ФАЗА: {phase_name}")
    
    def validate_all(self):
        """Выполнение всех проверок"""
        self.start_phase("ПРОВЕРКА ОКНА НАПОМИНАНИЯ О ЗАВЕРШЕНИИ АКЦИИ")
        self.validate_end_news()
        
        self.start_phase("ПРОВЕРКА ОКНА ДВОЙНЫХ ОЧКОВ")
        self.validate_double_points()
        
        self.start_phase("ПРОВЕРКА КУРСА ОБМЕНА КЭША НА ОЧКИ")
        self.validate_items_to_cash_exchange()
        
        self.print_summary()
        
    def validate_end_news(self):
        """Проверка окна напоминания о завершении акции"""
        # Получаем данные из требований для проверки
        end_news_req = self.requirements_by_alias.get('end news')
        
        if not end_news_req:
            self.log_error("Не найдены требования для 'end news' в таблице")
            return
        
        # 1. Проверяем даты from и to
        req_from = end_news_req.get('from', '')
        req_to = end_news_req.get('to', '')
        promo_from = self.end_news_promo.get('from', '')
        promo_to = self.end_news_promo.get('to', '')
        
        self.log_check(
            "end_news_dates_from",
            "Дата начала показа окна завершения акции",
            req_from == promo_from,
            req_from,
            promo_from
        )
        
        self.log_check(
            "end_news_dates_to",
            "Дата окончания показа окна завершения акции",
            req_to == promo_to,
            req_to,
            promo_to
        )
        
        # 2. Проверяем условия показа новостей
        # Ищем в фильтрах нужные условия
        filters = self.end_news_promo.get('filters', [])
        
        # Проверяем параметр "any"
        any_filter = next((f for f in filters if f.get('type') == 'ActionContain' and 
                         f.get('conditions', {}).get('actions', {}).get('compare') == 'any'), None)
        
        if any_filter:
            items = any_filter.get('conditions', {}).get('actions', {}).get('items', [])
            any_items_str = ','.join(map(str, items)) if isinstance(items, list) else str(items)
            req_any = end_news_req.get('any', '')
            
            self.log_check(
                "end_news_any_condition",
                "Условие показа 'any' окна завершения акции",
                str(req_any) == any_items_str,
                req_any,
                any_items_str
            )
        else:
            self.log_error("Не найдено условие 'ActionContain' с compare='any' в фильтрах окна завершения акции")
        
        # Проверяем параметр "not"
        not_filter = next((f for f in filters if f.get('type') == 'ActionContain' and 
                         f.get('conditions', {}).get('actions', {}).get('compare') == 'not'), None)
        
        if not_filter:
            items = not_filter.get('conditions', {}).get('actions', {}).get('items', [])
            not_items_str = ','.join(map(str, items)) if isinstance(items, list) else str(items)
            req_not = end_news_req.get('not', '')
            
            self.log_check(
                "end_news_not_condition",
                "Условие показа 'not' окна завершения акции",
                req_not == not_items_str,
                req_not,
                not_items_str
            )
        else:
            self.log_error("Не найдено условие 'ActionContain' с compare='not' в фильтрах окна завершения акции")
            
        # 3. Проверка соответствия значений "not" и параметра "seasonPassActions" в promo.json
        season_pass_actions = self.promo.get('parameters', {}).get('seasonPassActions', [])
        if season_pass_actions:
            season_pass_actions_str = ','.join(map(str, season_pass_actions)) if isinstance(season_pass_actions, list) else str(season_pass_actions)
            
            self.log_check(
                "end_news_season_pass_actions",
                "Соответствие значений 'not' и 'seasonPassActions'",
                req_not == season_pass_actions_str,
                req_not,
                season_pass_actions_str,
                "Значения 'not' из требований должны соответствовать 'seasonPassActions' в promo.json"
            )
        else:
            self.log_error("Не найден параметр 'seasonPassActions' в основном файле промо")

    def validate_double_points(self):
        """Проверка окна двойных очков"""
        # Получаем данные из требований для проверки
        double_points_req = self.requirements_by_alias.get('double points(2)')
        
        if not double_points_req:
            self.log_error("Не найдены требования для 'double points(2)' в таблице")
            return
        
        # 1. Проверяем даты from и to
        req_from = double_points_req.get('from', '')
        req_to = double_points_req.get('to', '')
        promo_from = self.double_points_promo.get('from', '')
        promo_to = self.double_points_promo.get('to', '')
        
        self.log_check(
            "double_points_dates_from",
            "Дата начала показа окна двойных очков",
            req_from == promo_from,
            req_from,
            promo_from
        )
        
        self.log_check(
            "double_points_dates_to",
            "Дата окончания показа окна двойных очков",
            req_to == promo_to,
            req_to,
            promo_to
        )
        
        # 2. Проверка даты включения множителя (MultiplierTurnOn)
        req_multiplier_date = double_points_req.get('MultiplierTurnOn', '')
        # Ищем параметр promotionAwardMultiplierTurnOn в основном промо
        promo_multiplier_date = self.promo.get('parameters', {}).get('promotionAwardMultiplierTurnOn', '')
        
        if req_multiplier_date:
            self.log_check(
                "double_points_multiplier_date",
                "Дата включения множителя",
                req_multiplier_date == promo_multiplier_date,
                req_multiplier_date,
                promo_multiplier_date or "Не найдено в основном промо",
                "Параметр promotionAwardMultiplierTurnOn в promo.json"
            )
        
        # 3. Проверка значения множителя из алиаса
        # Извлекаем значение множителя из алиаса 'double points(2)'
        multiplier_value = None
        alias = double_points_req.get('alias', '')
        if alias:
            # Находим значение в скобках
            match = re.search(r'\((\d+)\)', alias)
            if match:
                multiplier_value = match.group(1)
        
        # Получаем значение параметра promotionAwardMultiplier из основного промо
        promo_multiplier_value = str(self.promo.get('parameters', {}).get('promotionAwardMultiplier', ''))
        
        if multiplier_value:
            self.log_check(
                "double_points_multiplier_value",
                "Значение множителя очков",
                multiplier_value == promo_multiplier_value,
                multiplier_value,
                promo_multiplier_value or "Не найдено в основном промо",
                "Параметр promotionAwardMultiplier в promo.json"
            )
        else:
            self.log_warning("Не удалось извлечь значение множителя из алиаса 'double points(2)'")

    def validate_items_to_cash_exchange(self):
        """Проверка курса обмена кэша на очки"""
        # Получаем данные из требований для проверки
        exchange_req = self.requirements_by_alias.get('itemsToCashExchange(15)')
        
        if not exchange_req:
            # Если точного совпадения нет, ищем по части алиаса
            for alias, req in self.requirements_by_alias.items():
                if alias and 'itemsToCashExchange' in alias:
                    exchange_req = req
                    break
        
        if not exchange_req:
            self.log_error("Не найдены требования для 'itemsToCashExchange' в таблице")
            return
        
        # Извлекаем значение курса из алиаса
        exchange_rate = None
        alias = exchange_req.get('alias', '')
        if alias:
            # Находим значение в скобках
            match = re.search(r'\((\d+)\)', alias)
            if match:
                exchange_rate = match.group(1)
        
        # Получаем значение параметра itemsToCashExchange из основного промо
        promo_exchange_rate = str(self.promo.get('parameters', {}).get('itemsToCashExchange', ''))
        
        if exchange_rate:
            self.log_check(
                "items_to_cash_exchange_rate",
                "Курс обмена кэша на очки",
                exchange_rate == promo_exchange_rate,
                exchange_rate,
                promo_exchange_rate or "Не найдено в основном промо",
                "Параметр itemsToCashExchange в promo.json"
            )
        else:
            self.log_warning("Не удалось извлечь значение курса обмена из алиаса для itemsToCashExchange")
    
    def print_summary(self):
        """Вывод итогов проверок"""
        self.print_header("РЕЗУЛЬТАТЫ ПРОВЕРОК")
        
        total = self.stats["total_checks"]
        passed = self.stats["passed_checks"]
        failed = self.stats["failed_checks"]
        warnings = self.stats["warning_checks"]
        
        pass_percent = (passed / total * 100) if total > 0 else 0
        
        summary = f"Всего проверок: {total}\n"
        summary += f"Успешных: {passed} ({pass_percent:.1f}%)\n"
        summary += f"Ошибок: {failed}\n"
        summary += f"Предупреждений: {warnings}\n"
        
        self.log_info(summary)
        
        if self.errors:
            self.log_info(f"\nОШИБКИ ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                self.log_info(f"{i}. {error}")
        
        if self.warnings:
            self.log_info(f"\nПРЕДУПРЕЖДЕНИЯ ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                self.log_info(f"{i}. {warning}")
    
    def save_detailed_log(self, output_file="validation_detailed.log"):
        """Сохранение детального лога в файл"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for log in self.info_logs:
                    f.write(log + "\n")
            self.log_info(f"Детальный лог сохранен в файл: {output_file}")
        except Exception as e:
            self.log_error(f"Ошибка при сохранении лога: {str(e)}")
            
    def save_report_to_csv(self, output_file="validation_report.csv"):
        """Сохранение отчета с ошибками в CSV файл"""
        try:
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # Заголовок
                writer.writerow(['Проверка', 'ID', 'Ожидалось', 'Фактически', 'Результат', 'Детали'])
                
                # Для ошибок end news
                end_news_req = self.requirements_by_alias.get('end news', {})
                end_news_name = end_news_req.get('alias', 'end_news')
                for check_id, errors in self.config_errors.items():
                    if check_id and check_id.startswith('end_news'):
                        for error in errors:
                            writer.writerow([
                                error.get('check', ''),
                                end_news_name,
                                error.get('expected', ''),
                                error.get('actual', ''),
                                'ОШИБКА',
                                error.get('details', '')
                            ])
                
                # Для ошибок double points
                double_points_req = self.requirements_by_alias.get('double points(2)', {})
                double_points_name = double_points_req.get('alias', 'double_points')
                for check_id, errors in self.config_errors.items():
                    if check_id and check_id.startswith('double_points'):
                        for error in errors:
                            writer.writerow([
                                error.get('check', ''),
                                double_points_name,
                                error.get('expected', ''),
                                error.get('actual', ''),
                                'ОШИБКА',
                                error.get('details', '')
                            ])
                
                # Для ошибок курса обмена
                for check_id, errors in self.config_errors.items():
                    if check_id and check_id.startswith('items_to_cash'):
                        for error in errors:
                            writer.writerow([
                                error.get('check', ''),
                                'itemsToCashExchange',
                                error.get('expected', ''),
                                error.get('actual', ''),
                                'ОШИБКА',
                                error.get('details', '')
                            ])
                            
            self.log_info(f"Отчет с ошибками сохранен в файл: {output_file}")
        except Exception as e:
            self.log_error(f"Ошибка при сохранении отчета: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Валидация окон напоминаний и двойных очков')
    parser.add_argument('--end-news-promo', default='end-news-promo.json', help='Путь к файлу промо окна завершения акции')
    parser.add_argument('--double-points-promo', default='double-points-promo.json', help='Путь к файлу промо двойных очков')
    parser.add_argument('--promo', default='promo.json', help='Путь к основному файлу промо')
    parser.add_argument('--requirements', default='requirements.csv', help='Путь к файлу требований')
    parser.add_argument('--quiet', action='store_true', help='Отключить подробный вывод')
    parser.add_argument('--json', action='store_true', help='Вывод в формате JSON')
    parser.add_argument('--log', default='validation_detailed.log', help='Путь к файлу для сохранения детального лога')
    parser.add_argument('--csv', default='validation_report.csv', help='Путь к файлу для сохранения отчета в формате CSV')
    
    args = parser.parse_args()
    
    validator = EndNewsDoublePointsValidator(
        end_news_promo_file=args.end_news_promo,
        double_points_promo_file=args.double_points_promo,
        promo_file=args.promo,
        requirements_file=args.requirements,
        verbose=not args.quiet,
        json_output=args.json
    )
    
    validator.validate_all()
    validator.save_detailed_log(args.log)
    validator.save_report_to_csv(args.csv)

if __name__ == "__main__":
    main() 