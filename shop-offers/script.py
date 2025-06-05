import json
import csv
import os
import sys
import argparse
from datetime import datetime
import textwrap

class ShopOffersValidator:
    def __init__(self, promo_file="promo.json", requirements_file="requirements.csv", 
                 actions_file="actions.json", offers_file="offers.json", verbose=True, json_output=False):
        """
        Инициализация валидатора конфигурации офферов магазина.
        
        Args:
            promo_file (str): Путь к JSON-файлу с промо-акцией
            requirements_file (str): Путь к CSV-файлу с требованиями
            actions_file (str): Путь к JSON-файлу с действиями
            offers_file (str): Путь к JSON-файлу с офферами
            verbose (bool): Подробное логирование
            json_output (bool): Вывод в формате JSON (отключает текстовый вывод)
        """
        self.errors = []
        self.warnings = []
        self.info_logs = []
        self.verbose = verbose
        self.json_output = json_output
        
        # Алиасы с особыми правилами проверки
        self.special_aliases = {
            "Выдача очков подписки": {
                "skip_promo_check": True,  # Не проверять наличие в awards promo.json
                "skip_offer_check": True   # Не проверять наличие Offer ID
            }
        }
        
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
        
        self.print_header("ВАЛИДАЦИЯ ОФФЕРОВ МАГАЗИНА")
        self.log_info(f"Файлы для проверки:")
        self.log_info(f"- Промо: {promo_file}")
        self.log_info(f"- Требования: {requirements_file}")
        self.log_info(f"- Экшены: {actions_file}")
        self.log_info(f"- Офферы: {offers_file}")
        
        # Загрузка данных
        self.promo = self._load_json(promo_file)
        self.requirements = self._load_csv(requirements_file)
        self.actions = self._load_json(actions_file)
        self.offers = self._load_json(offers_file)
        
        # Создание словарей для быстрого поиска
        # Словарь для хранения экшенов из requirements.csv
        self.requirements_by_action_id = {}
        for req in self.requirements:
            if 'Action' in req and req['Action']:
                try:
                    action_id = int(req['Action'])
                    self.requirements_by_action_id[action_id] = req
                except (ValueError, TypeError):
                    self.log_warning(f"Некорректный Action ID в требованиях: {req.get('Action')}")

        # Словарь для быстрого доступа к офферам по ID
        self.offers_by_id = {}
        if isinstance(self.offers, dict):
            # Проверяем наличие структуры offers
            if "offers" in self.offers:
                # Получаем список офферов из вложенных массивов
                for offer_group in self.offers["offers"]:
                    for offer_list in offer_group:
                        for offer in offer_list:
                            if isinstance(offer, dict) and "@id" in offer:
                                self.offers_by_id[offer["@id"]] = offer
            # А также проверяем наличие структуры prices
            if "prices" in self.offers:
                for price in self.offers["prices"]:
                    if "@id" in price:
                        self.offers_by_id[price["@id"]] = price
        
        # Словарь для хранения всех экшенов из actions.json
        self.actions_by_id = {}
        for action in self.actions:
            action_id = action.get('@id')
            if action_id:
                self.actions_by_id[int(action_id)] = action
        
        # Получаем список экшенов из промо
        self.promo_action_ids = set()
        if isinstance(self.promo, dict) and "awards" in self.promo:
            self.promo_action_ids = set(self.promo.get('awards', []))
        
        self.log_info(f"Загружено {len(self.requirements_by_action_id)} записей из таблицы требований")
        self.log_info(f"Загружено {len(self.actions_by_id)} записей из файла экшенов")
        self.log_info(f"Загружено {len(self.offers_by_id)} офферов из файла offers")
        self.log_info(f"Найдено {len(self.promo_action_ids)} действий в промо")
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
            if action_id not in self.offer_errors:
                self.offer_errors[action_id] = []
            
            error_details = {
                "check": check_name,
                "expected": expected,
                "actual": actual,
                "details": details,
                "tag": check_tag
            }
            self.offer_errors[action_id].append(error_details)
            
            # Добавляем в общий список ошибок
            error_msg = f"Action {action_id}: {check_name}"
            if expected is not None and actual is not None:
                error_msg += f" (ожидалось: {expected}, получено: {actual})"
            if details:
                error_msg += f" - {details}"
            self.errors.append(error_msg)
        
        self.info_logs.append(log_msg)
        
        if self.verbose and not self.json_output:
            print(f"{status} Action {action_id}: {check_name}{extra_info}")
            if details and not result:
                print(f"  {details}")
    
    def log_warning(self, message, action_id=None):
        """Логирование предупреждений"""
        self.stats["warning_checks"] += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if action_id is not None:
            log_msg = f"[WARNING] {timestamp} - Action {action_id}: {message}"
            display_msg = f"{self.YELLOW}[ВНИМАНИЕ]{self.RESET} Action {action_id}: {message}"
            
            # Добавляем предупреждение в список для этого action_id
            if action_id not in self.offer_errors:
                self.offer_errors[action_id] = []
            
            self.offer_errors[action_id].append({
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
            if action_id not in self.offer_errors:
                self.offer_errors[action_id] = []
            
            self.offer_errors[action_id].append({
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
        
        # Фаза 2: Проверка наград
        self.validate_action_rewards()
        
        # Фаза 3: Проверка наличия Action ID из требований в promo.json
        self.validate_action_ids_in_promo()
        
        # Фаза 4: Проверка связей Action и Offer
        self.validate_action_offer_links()
        
        # Вывод итогового отчёта
        self.print_summary()
        
    def validate_action_ids_in_actions(self):
        """Проверка наличия указанных Action ID из требований в actions.json"""
        self.start_phase("ПРОВЕРКА НАЛИЧИЯ ACTION ID В ACTIONS.JSON")
        
        for action_id, req in self.requirements_by_action_id.items():
            alias = req.get('alias', 'Неизвестно')
            exists = action_id in self.actions_by_id
            
            self.log_check(
                action_id, 
                f"Наличие Action ID в actions.json (алиас: {alias})",
                exists,
                "Присутствует",
                "Присутствует" if exists else "Отсутствует",
                None,
                "ACTION_EXISTS"
            )
            
    def validate_action_rewards(self):
        """Проверка наград в экшенах"""
        self.start_phase("ПРОВЕРКА НАГРАД В ЭКШЕНАХ")
        
        for action_id, req in self.requirements_by_action_id.items():
            alias = req.get('alias', 'Неизвестно')
            
            # Пропускаем проверку, если экшена нет в actions.json
            if action_id not in self.actions_by_id:
                self.log_warning(f"Пропуск проверки наград для отсутствующего экшена {action_id} ({alias})", action_id)
                continue
            
            action = self.actions_by_id[action_id]
            awards = action.get('awards', [])
            
            # Проверяем каждую награду из требований
            for column, value in req.items():
                if not value or not column.startswith('Award_'):
                    continue
                
                # Извлекаем item_id и ожидаемое количество из столбца
                # Формат столбца: Award_points(17909) или Award_techitem(17907)
                parts = column.split('(')
                if len(parts) != 2:
                    self.log_warning(f"Неправильный формат столбца награды: {column}", action_id)
                    continue
                
                item_type = parts[0].replace('Award_', '')
                item_id_str = parts[1].replace(')', '')
                try:
                    item_id = int(item_id_str)
                    expected_count = int(value)
                except (ValueError, TypeError):
                    self.log_warning(f"Неправильное значение награды: {value} для {column}", action_id)
                    continue
                
                # Ищем соответствующую награду в экшене
                found = False
                actual_count = 0
                
                for award in awards:
                    if award.get('type') == 'item' and award.get('itemId') == item_id:
                        found = True
                        actual_count = award.get('count', 0)
                        break
                
                self.log_check(
                    action_id,
                    f"Награда {item_id} ({item_type}) в экшене",
                    found and actual_count == expected_count,
                    expected_count,
                    actual_count if found else "Не найдено",
                    None,
                    "AWARD_CHECK"
                )
            
            # Проверка необходимых ресурсов (needResources)
            need_resources = action.get('needResources', [])
            
            for column, value in req.items():
                if not value or not column.startswith('NeedResources'):
                    continue
                
                # Извлекаем item_id и ожидаемое количество из столбца
                # Формат столбца: NeedResources(17907)
                parts = column.split('(')
                if len(parts) != 2:
                    self.log_warning(f"Неправильный формат столбца ресурсов: {column}", action_id)
                    continue
                
                item_id_str = parts[1].replace(')', '')
                try:
                    item_id = int(item_id_str)
                    expected_count = int(value)
                except (ValueError, TypeError):
                    self.log_warning(f"Неправильное значение ресурса: {value} для {column}", action_id)
                    continue
                
                # Ищем соответствующий ресурс в экшене
                found = False
                actual_count = 0
                
                for resource in need_resources:
                    if resource.get('type') == 'item' and resource.get('itemId') == item_id:
                        found = True
                        actual_count = resource.get('count', 0)
                        break
                
                self.log_check(
                    action_id,
                    f"Необходимый ресурс {item_id} в экшене",
                    found and actual_count == expected_count,
                    expected_count,
                    actual_count if found else "Не найдено",
                    None,
                    "NEED_RESOURCE_CHECK"
                )
    
    def validate_action_ids_in_promo(self):
        """Проверка наличия указанных Action ID в соответствующих параметрах promo.json"""
        self.start_phase("ПРОВЕРКА ACTION ID В ПАРАМЕТРАХ PROMO.JSON")
        
        # Проверяем наличие секции parameters
        if "parameters" not in self.promo:
            self.log_warning("Параметр parameters отсутствует в promo.json")
            return
        
        params = self.promo["parameters"]
            
        # Проверяем наличие параметра buyWindowParams
        if "buyWindowParams" not in params:
            self.log_warning("Параметр buyWindowParams отсутствует в promo.json.parameters")
            return
            
        buy_window_params = params["buyWindowParams"]
        
        # Особые проверки для офферов магазина
        special_offer_checks = {
            "passOffer": "passOffer",
            "mainOffer": "mainOffer",
            "subscriptionOffer": "subscriptionOffer"
        }
        
        for action_id, req in self.requirements_by_action_id.items():
            alias = req.get('alias', 'Неизвестно')
            
            # Если это один из офферов магазина, проверяем в соответствующем параметре
            if alias in special_offer_checks:
                param_name = special_offer_checks[alias]
                expected_action_id = action_id
                
                # Проверяем наличие параметра в buyWindowParams
                if param_name in buy_window_params:
                    offer_params = buy_window_params[param_name]
                    
                    # Проверяем наличие actionId в параметрах оффера
                    if "actionId" in offer_params:
                        actual_action_id = offer_params["actionId"]
                        is_match = str(actual_action_id) == str(expected_action_id)
                        
                        self.log_check(
                            action_id, 
                            f"Action ID в параметре parameters.buyWindowParams.{param_name}",
                            is_match,
                            expected_action_id,
                            actual_action_id,
                            None,
                            "ACTION_IN_PROMO_PARAM"
                        )
                    else:
                        self.log_check(
                            action_id, 
                            f"Наличие actionId в parameters.buyWindowParams.{param_name}",
                            False,
                            "Присутствует",
                            "Отсутствует",
                            None,
                            "ACTION_ID_EXISTS"
                        )
                else:
                    self.log_check(
                        action_id, 
                        f"Наличие параметра {param_name} в parameters.buyWindowParams",
                        False,
                        "Присутствует",
                        "Отсутствует",
                        None,
                        "OFFER_PARAM_EXISTS"
                    )
            else:
                # Проверяем, является ли этот алиас особым случаем, для которого не нужно проверять наличие в awards
                special_config = self.special_aliases.get(alias)
                if special_config and special_config.get("skip_promo_check"):
                    self.log_info(f"Пропуск проверки наличия в awards для {alias} (Action {action_id})")
                    continue
                
                # Для остальных экшенов проверяем наличие в массиве awards
                exists = action_id in self.promo_action_ids
                
                self.log_check(
                    action_id, 
                    f"Наличие Action ID в awards promo.json (алиас: {alias})",
                    exists,
                    "Присутствует",
                    "Присутствует" if exists else "Отсутствует",
                    None,
                    "ACTION_IN_PROMO_AWARDS"
                )
    
    def validate_action_offer_links(self):
        """Проверка связей между Action и Offer"""
        self.start_phase("ПРОВЕРКА СВЯЗЕЙ ACTION И OFFER")
        
        for action_id, req in self.requirements_by_action_id.items():
            alias = req.get('alias', 'Неизвестно')
            
            # Проверяем, является ли этот алиас особым случаем, для которого не нужно проверять offer
            special_config = self.special_aliases.get(alias)
            if special_config and special_config.get("skip_offer_check"):
                self.log_info(f"Пропуск проверки Offer для {alias} (Action {action_id})")
                continue
            
            # Получаем Offer ID из требований
            offer_id_str = req.get('Offer', '')
            
            # Если offer_id не определен, пропускаем
            if not offer_id_str:
                self.log_warning(f"Не указан Offer ID для Action {action_id} ({alias})", action_id)
                continue
                
            try:
                offer_id = int(offer_id_str)
            except (ValueError, TypeError):
                self.log_warning(f"Некорректный Offer ID: {offer_id_str} для Action {action_id}", action_id)
                continue
            
            # Проверяем наличие оффера в offers.json
            offer_exists = offer_id in self.offers_by_id
            
            self.log_check(
                action_id,
                f"Наличие Offer {offer_id} в offers.json",
                offer_exists,
                "Присутствует",
                "Присутствует" if offer_exists else "Отсутствует",
                None,
                "OFFER_EXISTS"
            )
            
            if not offer_exists:
                continue
                
            # Проверяем соответствие Action и Offer
            offer = self.offers_by_id[offer_id]
            action_id_in_offer = offer.get('actionId')
            
            # Если в оффере нет поля actionId, то это ошибка
            if action_id_in_offer is None:
                self.log_check(
                    action_id,
                    f"Offer {offer_id} содержит поле actionId",
                    False,
                    "Присутствует",
                    "Отсутствует",
                    None,
                    "ACTION_ID_IN_OFFER"
                )
                continue
                
            # Проверяем соответствие Action ID в Offer с ожидаемым Action ID
            try:
                action_id_in_offer = int(action_id_in_offer)
                is_match = action_id_in_offer == action_id
            except (ValueError, TypeError):
                self.log_check(
                    action_id,
                    f"Корректный ActionId в Offer {offer_id}",
                    False,
                    action_id,
                    action_id_in_offer,
                    "Некорректный тип данных для actionId в оффере",
                    "ACTION_ID_TYPE"
                )
                continue
            
            self.log_check(
                action_id,
                f"Action ID в Offer {offer_id} соответствует ожидаемому",
                is_match,
                action_id,
                action_id_in_offer,
                None,
                "ACTION_OFFER_MATCH"
            )
            
            # Проверяем цену через packet_id (новая проверка)
            expected_price = req.get('Price', '').strip()
            if expected_price and 'packet_id' in offer:
                # Удаляем символ доллара из ожидаемой цены
                if expected_price.startswith('$'):
                    expected_price = expected_price[1:]
                
                try:
                    expected_price_float = float(expected_price)
                    packet_id = offer.get('packet_id')
                    
                    # Ищем цену в массиве prices по packet_id
                    price_found = False
                    actual_price = None
                    
                    if isinstance(self.offers, dict) and "prices" in self.offers:
                        for price in self.offers["prices"]:
                            if price.get('@id') == packet_id:
                                actual_price = price.get('USD')
                                price_found = True
                                break
                    
                    if price_found and actual_price is not None:
                        actual_price_float = float(actual_price)
                        price_match = abs(actual_price_float - expected_price_float) < 0.001
                        
                        self.log_check(
                            action_id,
                            f"Цена Offer {offer_id} (packet_id: {packet_id}) соответствует ожидаемой",
                            price_match,
                            f"${expected_price_float}",
                            f"${actual_price_float}",
                            None,
                            "PRICE_MATCH"
                        )
                    else:
                        self.log_check(
                            action_id,
                            f"Цена USD для Offer {offer_id} (packet_id: {packet_id}) найдена",
                            False,
                            f"${expected_price_float}",
                            "Не найдено" if not price_found else "USD отсутствует",
                            None,
                            "PRICE_EXISTS"
                        )
                except (ValueError, TypeError):
                    self.log_warning(f"Некорректный формат цены: {expected_price} или packet_id: {offer.get('packet_id')} для Action {action_id}", action_id)
            elif expected_price:
                # Проверяем цену напрямую (старый вариант)
                # Удаляем символ доллара из ожидаемой цены
                if expected_price.startswith('$'):
                    expected_price = expected_price[1:]
                    
                try:
                    expected_price_float = float(expected_price)
                    actual_price = offer.get('USD')
                    
                    if actual_price is not None:
                        actual_price_float = float(actual_price)
                        price_match = abs(actual_price_float - expected_price_float) < 0.001
                        
                        self.log_check(
                            action_id,
                            f"Цена Offer {offer_id} соответствует ожидаемой (прямая проверка)",
                            price_match,
                            f"${expected_price_float}",
                            f"${actual_price_float}",
                            None,
                            "PRICE_DIRECT_MATCH"
                        )
                    else:
                        self.log_check(
                            action_id,
                            f"Цена USD для Offer {offer_id} определена",
                            False,
                            f"${expected_price_float}",
                            "Отсутствует",
                            None,
                            "PRICE_EXISTS"
                        )
                except (ValueError, TypeError):
                    self.log_warning(f"Некорректный формат цены: {expected_price} для Action {action_id}", action_id)
            else:
                # Если цена не указана в requirements.csv, выдаем предупреждение
                self.log_warning(f"Не указана цена для Action {action_id} ({alias})", action_id)
    
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
                writer.writerow(["Action ID", "Проверка", "Результат", "Ожидаемое", "Фактическое", "Детали"])
                
                for action_id, errors in self.offer_errors.items():
                    for error in errors:
                        writer.writerow([
                            action_id,
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
    parser = argparse.ArgumentParser(description='Валидатор офферов магазина')
    parser.add_argument('--promo', default="promo.json", help='Путь к файлу promo.json')
    parser.add_argument('--requirements', default="requirements.csv", help='Путь к файлу requirements.csv')
    parser.add_argument('--actions', default="actions.json", help='Путь к файлу actions.json')
    parser.add_argument('--offers', default="offers.json", help='Путь к файлу offers.json')
    parser.add_argument('--report', default="validation_report.csv", help='Путь к файлу отчета')
    parser.add_argument('--log', default="validation_detailed.log", help='Путь к файлу лога')
    parser.add_argument('--quiet', action='store_true', help='Минимальный вывод в консоль')
    parser.add_argument('--json', action='store_true', help='Вывод в формате JSON')
    
    args = parser.parse_args()
    
    validator = ShopOffersValidator(
        promo_file=args.promo,
        requirements_file=args.requirements,
        actions_file=args.actions,
        offers_file=args.offers,
        verbose=not args.quiet,
        json_output=args.json
    )
    
    validator.validate_all()
    validator.save_report_to_csv(args.report)
    validator.save_detailed_log(args.log)

if __name__ == "__main__":
    main() 