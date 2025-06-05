import json
import csv
import os
import sys
import argparse
from datetime import datetime
import textwrap

class SeasonPassValidator:
    def __init__(self, promo_file="promo.json", requirements_file="requirements.csv", 
                 actions_file="actions.json", verbose=True, json_output=False):
        """
        Инициализация валидатора конфигурации сезонного пропуска.
        
        Args:
            promo_file (str): Путь к JSON-файлу с промо-акцией
            requirements_file (str): Путь к CSV-файлу с требованиями
            actions_file (str): Путь к JSON-файлу с действиями
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
            "warning_checks": 0,
            "free_action_ids_count": 0,
            "paid_action_ids_count": 0,
            "promo_action_ids_count": 0,
            "actions_file_count": 0
        }
        
        # Прогресс по этапам
        self.current_phase = ""
        
        # Ошибки для сводной таблицы
        self.action_errors = {}
        
        self.print_header("ВАЛИДАЦИЯ НАГРАД СЕЗОННОГО ПРОПУСКА")
        self.log_info(f"Файлы для проверки:")
        self.log_info(f"- Промо: {promo_file}")
        self.log_info(f"- Требования: {requirements_file}")
        self.log_info(f"- Экшены: {actions_file}")
        
        # Загрузка данных
        self.promo = self._load_json(promo_file)
        self.requirements = self._load_csv(requirements_file)
        self.actions = self._load_json(actions_file)
        
        # Получаем информацию о сезонном пропуске
        self.season_pass_actions = self._get_season_pass_actions()
        if self.season_pass_actions:
            self.log_info(f"Извлечены ID сезонного пропуска: {self.season_pass_actions}")
        
        # Создание словарей для быстрого поиска
        # Словарь для хранения action_free из требований
        self.free_actions = {int(req['action_free']): req for req in self.requirements if 'action_free' in req and req['action_free']}
        # Словарь для хранения action_paid из требований
        self.paid_actions = {int(req['action_paid']): req for req in self.requirements if 'action_paid' in req and req['action_paid']}
        
        # Словарь для хранения всех экшенов из actions.json
        self.actions_by_id = {}
        for action in self.actions:
            action_id = action.get('@id')
            if action_id:
                self.actions_by_id[int(action_id)] = action
        
        # Получаем список экшенов из промо
        self.promo_action_ids = set(self.promo.get('awards', []))
        
        # Подсчет элементов
        self.stats["free_action_ids_count"] = len(self.free_actions)
        self.stats["paid_action_ids_count"] = len(self.paid_actions)
        self.stats["promo_action_ids_count"] = len(self.promo_action_ids)
        self.stats["actions_file_count"] = len(self.actions_by_id)
        
        self.log_info(f"Загружено {self.stats['free_action_ids_count']} бесплатных наград из таблицы требований")
        self.log_info(f"Загружено {self.stats['paid_action_ids_count']} платных наград из таблицы требований")
        self.log_info(f"Найдено {self.stats['promo_action_ids_count']} наград в промо")
        self.log_info(f"Найдено {self.stats['actions_file_count']} записей в файле экшенов")
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
            
    def log_check(self, action_id, check_name, result, expected=None, actual=None, details=None, check_tag=None):
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
            log_msg = f"[CHECK:OK] {timestamp} - Action {action_id}: {check_name}{extra_info}"
        else:
            self.stats["failed_checks"] += 1
            status = f"{self.RED}✗ ОШИБКА{self.RESET}"
            log_msg = f"[CHECK:FAIL] {timestamp} - Action {action_id}: {check_name}{extra_info}"
            
            # Добавляем ошибку в список ошибок для этого action_id
            if action_id not in self.action_errors:
                self.action_errors[action_id] = []
            
            error_details = {
                "check": check_name,
                "expected": expected,
                "actual": actual,
                "details": details,
                "tag": check_tag
            }
            self.action_errors[action_id].append(error_details)
            
            # Добавляем в общий список ошибок
            error_msg = f"Action {action_id}: {check_name}"
            if expected is not None and actual is not None:
                error_msg += f" (ожидалось: {expected}, получено: {actual})"
            if details:
                error_msg += f" - {details}"
            self.errors.append(error_msg)
        
        self.info_logs.append(log_msg)
        
        if self.verbose and not self.json_output:
            # Форматируем вывод для удобства чтения
            if expected is not None and actual is not None:
                if isinstance(expected, dict) or isinstance(actual, dict):
                    expected_str = json.dumps(expected, ensure_ascii=False, indent=2)
                    actual_str = json.dumps(actual, ensure_ascii=False, indent=2)
                    msg = f"{status} Action {action_id}: {check_name}\n"
                    msg += f"  Ожидалось:\n{textwrap.indent(expected_str, '    ')}\n"
                    msg += f"  Получено:\n{textwrap.indent(actual_str, '    ')}"
                    if details:
                        msg += f"\n  {details}"
                    print(msg)
                else:
                    print(f"{status} Action {action_id}: {check_name}{extra_info}")
                    if details:
                        print(f"  {details}")
            else:
                print(f"{status} Action {action_id}: {check_name}")
                if details:
                    print(f"  {details}")
    
    def log_warning(self, message, action_id=None):
        """Логирование предупреждений"""
        self.stats["warning_checks"] += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if action_id is not None:
            log_msg = f"[WARNING] {timestamp} - Action {action_id}: {message}"
            display_msg = f"{self.YELLOW}[ВНИМАНИЕ]{self.RESET} Action {action_id}: {message}"
            
            # Добавляем предупреждение в список для этого action_id
            if action_id not in self.action_errors:
                self.action_errors[action_id] = []
            
            self.action_errors[action_id].append({
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
    
    def log_error(self, message, action_id=None):
        """Логирование ошибок"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if action_id is not None:
            log_msg = f"[ERROR] {timestamp} - Action {action_id}: {message}"
            display_msg = f"{self.RED}[ОШИБКА]{self.RESET} Action {action_id}: {message}"
            
            # Добавляем ошибку в список для этого action_id
            if action_id not in self.action_errors:
                self.action_errors[action_id] = []
            
            self.action_errors[action_id].append({
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
        self.print_header(phase_name)
    
    def validate_all(self):
        """Выполнение всех проверок"""
        # Фаза 1: Проверка наличия экшенов
        self.start_phase("ФАЗА 1: ПРОВЕРКА НАЛИЧИЯ ЭКШЕНОВ")
        self.validate_action_ids_in_promo()
        self.validate_action_ids_in_actions()
        
        # Фаза 2: Проверка содержимого экшенов
        self.start_phase("ФАЗА 2: ПРОВЕРКА СОДЕРЖИМОГО ЭКШЕНОВ")
        self.validate_action_content()
        
        # Фаза 3: Проверка параметра needAction
        self.start_phase("ФАЗА 3: ПРОВЕРКА ПАРАМЕТРА NEEDACTION")
        self.validate_need_action()
        
        # Вывод результатов
        self.print_summary()
        
    def validate_action_ids_in_promo(self):
        """Проверка наличия всех action_free и action_paid из requirements в promo"""
        self.log_info("Проверка наличия всех action_free и action_paid из requirements в promo")
        
        # 1. Проверяем, что все action_free из requirements есть в promo
        for action_id in self.free_actions:
            is_in_promo = action_id in self.promo_action_ids
            self.log_check(
                action_id,
                "Наличие action_free в промо",
                is_in_promo,
                "В списке наград промо",
                "Присутствует" if is_in_promo else "Отсутствует",
                "Action_free должен присутствовать в списке наград промо",
                "ACTION_FREE_IN_PROMO"
            )
        
        # 2. Проверяем, что все action_paid из requirements есть в promo
        for action_id in self.paid_actions:
            is_in_promo = action_id in self.promo_action_ids
            self.log_check(
                action_id,
                "Наличие action_paid в промо",
                is_in_promo,
                "В списке наград промо",
                "Присутствует" if is_in_promo else "Отсутствует",
                "Action_paid должен присутствовать в списке наград промо",
                "ACTION_PAID_IN_PROMO"
            )
        
        # 3. Проверяем только те награды из промо, которые должны быть в требованиях
        # Собираем все action_id из таблицы требований
        all_required_action_ids = set(self.free_actions.keys()).union(set(self.paid_actions.keys()))
        
        for action_id in self.promo_action_ids:
            # Проверяем только те награды, которые должны быть явно указаны в таблице требований
            if action_id not in all_required_action_ids:
                # Проверяем наличие в служебных полях
                is_in_season_pass_actions = action_id in self.promo.get('parameters', {}).get('seasonPassActions', [])
                is_battlepass_action = action_id == self.promo.get('parameters', {}).get('battlepassAction', None)
                
                # Если награда находится в seasonPassActions или является battlepassAction, логируем это
                if is_in_season_pass_actions or is_battlepass_action:
                    self.log_info(f"Action {action_id} является служебным (seasonPassActions или battlepassAction) и не требует наличия в таблице")
                else:
                    self.log_info(f"Action {action_id} отсутствует в таблице требований, но это не ошибка - проверяем только экшены из таблицы")
                continue
            
            is_in_free = action_id in self.free_actions
            is_in_paid = action_id in self.paid_actions
            is_in_requirements = is_in_free or is_in_paid
            
            self.log_check(
                action_id,
                "Наличие награды из промо в требованиях",
                is_in_requirements,
                "В таблице требований",
                "Присутствует" if is_in_requirements else "Отсутствует",
                "Награда из промо должна присутствовать в таблице требований",
                "PROMO_AWARD_IN_REQUIREMENTS"
            )
    
    def validate_action_ids_in_actions(self):
        """Проверка наличия всех action_free и action_paid из requirements в actions.json"""
        self.log_info("Проверка наличия всех action_free и action_paid из requirements в файле actions.json")
        
        # 1. Проверяем, что все action_free из requirements есть в actions.json
        for action_id in self.free_actions:
            is_in_actions = action_id in self.actions_by_id
            self.log_check(
                action_id,
                "Наличие action_free в файле экшенов",
                is_in_actions,
                "В файле экшенов",
                "Присутствует" if is_in_actions else "Отсутствует",
                "Action_free должен присутствовать в файле экшенов",
                "ACTION_FREE_IN_ACTIONS"
            )
        
        # 2. Проверяем, что все action_paid из requirements есть в actions.json
        for action_id in self.paid_actions:
            is_in_actions = action_id in self.actions_by_id
            self.log_check(
                action_id,
                "Наличие action_paid в файле экшенов",
                is_in_actions,
                "В файле экшенов",
                "Присутствует" if is_in_actions else "Отсутствует",
                "Action_paid должен присутствовать в файле экшенов",
                "ACTION_PAID_IN_ACTIONS"
            )
    
    def validate_action_content(self):
        """Проверка содержимого экшенов"""
        self.log_info("Проверка содержимого экшенов")
        
        # 1. Проверяем содержимое action_free
        for action_id, requirement in self.free_actions.items():
            if action_id not in self.actions_by_id:
                self.log_warning(f"Action_free {action_id} отсутствует в файле экшенов, пропускаем проверку содержимого", action_id)
                continue
            
            action = self.actions_by_id[action_id]
            
            # Проверка needResources
            need_resources_value = requirement.get('needResources (17886)', '')
            if need_resources_value:
                need_resources_value = int(need_resources_value)
                
                # Если значение 0, пропускаем проверку наличия needResources
                if need_resources_value == 0:
                    self.log_info(f"Для action_id {action_id} не требуется проверка наличия needResources, так как значение в таблице = 0")
                else:
                    # Проверяем наличие и значение needResources в экшене
                    action_need_resources = action.get('needResources', [])
                    need_resources_found = False
                    need_resources_count_match = False
                    
                    for resource in action_need_resources:
                        if resource.get('type') == 'item' and resource.get('itemId') == 17886:
                            need_resources_found = True
                            need_resources_count_match = resource.get('count') == need_resources_value
                            break
                    
                    # Проверка наличия needResources
                    self.log_check(
                        action_id,
                        "Наличие needResources с itemId 17886 в экшене",
                        need_resources_found,
                        "Присутствует",
                        "Присутствует" if need_resources_found else "Отсутствует",
                        "NeedResources с itemId 17886 должен присутствовать в экшене",
                        "NEED_RESOURCES_PRESENCE"
                    )
                    
                    # Проверка значения count в needResources
                    if need_resources_found:
                        self.log_check(
                            action_id,
                            "Значение count в needResources",
                            need_resources_count_match,
                            need_resources_value,
                            resource.get('count') if 'resource' in locals() else None,
                            "Значение count в needResources должно соответствовать требованиям",
                            "NEED_RESOURCES_COUNT"
                        )
            else:
                # Если в требованиях needResources = 0 или пусто, то в экшене не должно быть needResources с itemId 17886
                action_need_resources = action.get('needResources', [])
                need_resources_found = False
                
                for resource in action_need_resources:
                    if resource.get('type') == 'item' and resource.get('itemId') == 17886:
                        need_resources_found = True
                        break
                
                # Если needResources = 0, в экшене не должно быть needResources с itemId 17886
                if need_resources_value == '0':
                    self.log_check(
                        action_id,
                        "Отсутствие needResources с itemId 17886 при значении 0",
                        not need_resources_found,
                        "Отсутствует",
                        "Отсутствует" if not need_resources_found else "Присутствует",
                        "NeedResources с itemId 17886 не должен присутствовать в экшене при значении 0",
                        "NEED_RESOURCES_ABSENCE"
                    )
            
            # Проверка наград (awards)
            award_type = requirement.get('award_1_type', '')
            award_id = requirement.get('award_1_id', '')
            award_qty = requirement.get('award_1_qty', '')
            
            if award_type and award_id and award_qty:
                award_qty = int(award_qty)
                
                # Преобразуем award_id в число, если это возможно
                if award_id.isdigit():
                    award_id = int(award_id)
                
                # Проверяем наличие и значения наград в экшене
                action_awards = action.get('awards', [])
                award_found = False
                award_count_match = False
                
                for award in action_awards:
                    # Проверка для типа "cash"
                    if award_type == 'cash' and award.get('type') == 'cash' and award_id == 'cash':
                        award_found = True
                        award_count_match = award.get('count') == award_qty
                        break
                    # Проверка для типа "season_currency"
                    elif award_type == 'season_currency' and award.get('type') == 'season_currency':
                        award_found = True
                        award_count_match = award.get('count') == award_qty
                        break
                    # Проверка для типа "item"
                    elif award_type == 'item' and award.get('type') == 'item' and award.get('itemId') == award_id:
                        award_found = True
                        award_count_match = award.get('count') == award_qty
                        break
                    # Проверка для типа "buff"
                    elif award_type == 'buff' and award.get('type') == 'buff' and award.get('id') == award_id:
                        award_found = True
                        award_count_match = award.get('count') == award_qty
                        break
                
                # Проверка наличия награды
                self.log_check(
                    action_id,
                    f"Наличие награды типа {award_type} с id {award_id} в экшене",
                    award_found,
                    "Присутствует",
                    "Присутствует" if award_found else "Отсутствует",
                    f"Награда типа {award_type} с id {award_id} должна присутствовать в экшене",
                    "AWARD_PRESENCE"
                )
                
                # Проверка значения count в награде
                if award_found:
                    self.log_check(
                        action_id,
                        f"Значение count в награде типа {award_type}",
                        award_count_match,
                        award_qty,
                        award.get('count') if 'award' in locals() else None,
                        "Значение count в награде должно соответствовать требованиям",
                        "AWARD_COUNT"
                    )
        
        # 2. Проверяем содержимое action_paid
        for action_id, requirement in self.paid_actions.items():
            if action_id not in self.actions_by_id:
                self.log_warning(f"Action_paid {action_id} отсутствует в файле экшенов, пропускаем проверку содержимого", action_id)
                continue
            
            action = self.actions_by_id[action_id]
            
            # Проверка наград (awards)
            award_type = requirement.get('award_2_type', '')
            award_id = requirement.get('award_2_id', '')
            award_qty = requirement.get('award_2_qty', '')
            
            if award_type and award_id and award_qty:
                award_qty = int(award_qty)
                
                # Преобразуем award_id в число, если это возможно
                if award_id.isdigit():
                    award_id = int(award_id)
                
                # Проверяем наличие и значения наград в экшене
                action_awards = action.get('awards', [])
                award_found = False
                award_count_match = False
                
                for award in action_awards:
                    # Проверка для типа "cash"
                    if award_type == 'cash' and award.get('type') == 'cash' and award_id == 'cash':
                        award_found = True
                        award_count_match = award.get('count') == award_qty
                        break
                    # Проверка для типа "season_currency"
                    elif award_type == 'season_currency' and award.get('type') == 'season_currency':
                        award_found = True
                        award_count_match = award.get('count') == award_qty
                        break
                    # Проверка для типа "item"
                    elif award_type == 'item' and award.get('type') == 'item' and award.get('itemId') == award_id:
                        award_found = True
                        award_count_match = award.get('count') == award_qty
                        break
                    # Проверка для типа "buff"
                    elif award_type == 'buff' and award.get('type') == 'buff' and award.get('id') == award_id:
                        award_found = True
                        award_count_match = award.get('count') == award_qty
                        break
                
                # Проверка наличия награды
                self.log_check(
                    action_id,
                    f"Наличие награды типа {award_type} с id {award_id} в экшене",
                    award_found,
                    "Присутствует",
                    "Присутствует" if award_found else "Отсутствует",
                    f"Награда типа {award_type} с id {award_id} должна присутствовать в экшене",
                    "AWARD_PRESENCE"
                )
                
                # Проверка значения count в награде
                if award_found:
                    self.log_check(
                        action_id,
                        f"Значение count в награде типа {award_type}",
                        award_count_match,
                        award_qty,
                        award.get('count') if 'award' in locals() else None,
                        "Значение count в награде должно соответствовать требованиям",
                        "AWARD_COUNT"
                    )
            
            # Проверка наличия needAction для платных наград
            need_action_values = action.get('needAction', '')
            has_need_action = bool(need_action_values)
            
            # Проверяем, что у платной награды есть поле needAction
            self.log_check(
                action_id,
                "Наличие поля needAction для платной награды",
                has_need_action,
                "Присутствует",
                "Присутствует" if has_need_action else "Отсутствует",
                "Поле needAction должно присутствовать для платной награды",
                "NEED_ACTION_PRESENCE"
            )
            
            # Проверяем, что значение needAction содержит ID сезонного пропуска
            if has_need_action:
                season_pass_actions = self.promo.get('parameters', {}).get('seasonPassActions', [])
                battle_pass_action = self.promo.get('parameters', {}).get('battlepassAction')
                
                need_action_ids = [int(id) for id in need_action_values.split(',')]
                
                # Проверяем, что хотя бы один из ID сезонного пропуска есть в needAction
                season_pass_found = any(id in need_action_ids for id in season_pass_actions)
                battle_pass_found = battle_pass_action in need_action_ids
                
                self.log_check(
                    action_id,
                    "Наличие ID сезонного пропуска в needAction",
                    season_pass_found or battle_pass_found,
                    "Присутствует",
                    "Присутствует" if season_pass_found or battle_pass_found else "Отсутствует",
                    "ID сезонного пропуска должен присутствовать в needAction",
                    "NEED_ACTION_SEASON_PASS"
                )
    
    def validate_need_action(self):
        """Проверка параметра needAction для платных наград"""
        if not self.season_pass_actions:
            self.log_warning("Невозможно проверить параметр needAction: не найдены ID сезонного пропуска")
            return
            
        for action_id in self.paid_actions.keys():
            if action_id not in self.actions_by_id:
                self.log_error(f"Невозможно проверить параметр needAction для экшена {action_id}, так как он отсутствует в конфиге", action_id)
                continue
                
            action_config = self.actions_by_id[action_id]
            need_action = action_config.get("needAction", "")
            
            # Проверяем наличие параметра needAction
            self.log_check(
                action_id,
                f"Наличие параметра needAction в экшене {action_id}",
                bool(need_action),
                "Присутствует",
                "Присутствует" if need_action else "Отсутствует",
                "Поле needAction должно присутствовать для платной награды",
                "NEED_ACTION_PRESENCE"
            )
            
            if not need_action:
                continue
                
            # Проверяем соответствие needAction и seasonPassActions
            self.log_check(
                action_id,
                f"Параметр needAction в экшене {action_id} соответствует ID сезонного пропуска",
                need_action == self.season_pass_actions,
                self.season_pass_actions,
                need_action,
                "Параметр needAction должен содержать точный список ID сезонного пропуска",
                "NEED_ACTION_VALUE"
            )
    
    def print_summary(self):
        """Вывод сводной информации о результатах проверки"""
        self.print_header("РЕЗУЛЬТАТЫ ПРОВЕРКИ")
        
        # Общая статистика
        print(f"Всего проверок: {self.stats['total_checks']}")
        print(f"{self.GREEN}Успешных проверок: {self.stats['passed_checks']}{self.RESET}")
        print(f"{self.RED}Проваленных проверок: {self.stats['failed_checks']}{self.RESET}")
        print(f"{self.YELLOW}Предупреждений: {self.stats['warning_checks']}{self.RESET}")
        
        # Вывод списка ошибок, если они есть
        if self.errors:
            print(f"\n{self.RED}Ошибки:{self.RESET}")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
        
        # Вывод списка предупреждений, если они есть
        if self.warnings:
            print(f"\n{self.YELLOW}Предупреждения:{self.RESET}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")
        
        # Вывод общего результата
        if self.stats['failed_checks'] == 0:
            print(f"\n{self.GREEN}{self.BOLD}Все проверки успешно пройдены!{self.RESET}")
        else:
            print(f"\n{self.RED}{self.BOLD}Обнаружены ошибки! Необходимо исправить найденные проблемы.{self.RESET}")
    
    def save_report_to_csv(self, output_file="validation_report.csv"):
        """Сохранение отчета в CSV-файл"""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Заголовок
                writer.writerow(["Action ID", "Проверка", "Результат", "Ожидаемое", "Фактическое", "Детали"])
                
                # Данные по ошибкам
                for action_id, errors in self.action_errors.items():
                    for error in errors:
                        writer.writerow([
                            action_id,
                            error.get("check"),
                            "Ошибка" if error.get("tag") != "WARNING" else "Предупреждение",
                            error.get("expected"),
                            error.get("actual"),
                            error.get("details")
                        ])
                
            self.log_info(f"Отчет сохранен в {output_file}")
        except Exception as e:
            self.log_error(f"Ошибка при сохранении отчета: {str(e)}")
    
    def save_detailed_log(self, output_file="validation_detailed.log"):
        """Сохранение подробного лога в текстовый файл"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for log_entry in self.info_logs:
                    f.write(log_entry + "\n")
                
            self.log_info(f"Подробный лог сохранен в {output_file}")
        except Exception as e:
            self.log_error(f"Ошибка при сохранении лога: {str(e)}")

    def _get_season_pass_actions(self):
        """Получаем список ID акций сезонного пропуска и формируем строку из них"""
        try:
            # Извлекаем параметр seasonPassActions из promo.json
            params = self.promo.get("parameters", {})
            season_pass_actions = params.get("seasonPassActions", [])
            
            if not season_pass_actions:
                self.log_warning("В promo.json не найден параметр seasonPassActions")
                return None
                
            # Формируем строку в формате id1,id2,...
            season_pass_str = ",".join(map(str, season_pass_actions))
            return season_pass_str
        except Exception as e:
            self.log_error(f"Ошибка при получении ID сезонного пропуска: {str(e)}")
            return None

def main():
    """Основная функция запуска валидатора"""
    parser = argparse.ArgumentParser(description='Валидатор конфигурации сезонного пропуска')
    parser.add_argument('--promo', default='promo.json', help='Путь к JSON-файлу с промо-акцией')
    parser.add_argument('--requirements', default='requirements.csv', help='Путь к CSV-файлу с требованиями')
    parser.add_argument('--actions', default='actions.json', help='Путь к JSON-файлу с действиями')
    parser.add_argument('--verbose', action='store_true', help='Подробное логирование')
    parser.add_argument('--json-output', action='store_true', help='Вывод в формате JSON (отключает текстовый вывод)')
    parser.add_argument('--report', default='validation_report.csv', help='Имя файла для сохранения отчета')
    parser.add_argument('--log', default='validation_detailed.log', help='Имя файла для сохранения детального лога')
    
    args = parser.parse_args()
    
    # Создаем экземпляр валидатора
    validator = SeasonPassValidator(
        promo_file=args.promo,
        requirements_file=args.requirements,
        actions_file=args.actions,
        verbose=args.verbose,
        json_output=args.json_output
    )
    
    # Выполняем валидацию
    validator.validate_all()
    
    # Сохраняем отчеты
    validator.save_report_to_csv(args.report)
    validator.save_detailed_log(args.log)

if __name__ == "__main__":
    main() 