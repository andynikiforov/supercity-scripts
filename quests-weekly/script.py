#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Скрипт для проверки еженедельных квестов в SeasonPass

import json
import csv
import os
import sys
import argparse
from datetime import datetime
import textwrap

class QuestsValidator:
    def __init__(self, promo_file="promo.json", requirements_file="requirements.csv", 
                 actions_file="actions.json", verbose=True, json_output=False):
        """
        Инициализация валидатора конфигурации еженедельных квестов SeasonPass.
        
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
            "complexity_ids_count": 0,
            "promo_quests_count": 0,
            "actions_count": 0
        }
        
        # Прогресс по этапам
        self.current_phase = ""
        
        # Ошибки для сводной таблицы
        self.quest_errors = {}
        
        self.print_header("ВАЛИДАЦИЯ ЕЖЕНЕДЕЛЬНЫХ КВЕСТОВ СЕЗОННОГО ПРОПУСКА")
        self.log_info(f"Файлы для проверки:")
        self.log_info(f"- Промо: {promo_file}")
        self.log_info(f"- Требования: {requirements_file}")
        self.log_info(f"- Экшены: {actions_file}")
        
        # Загрузка данных
        self.promo = self._load_json(promo_file)
        self.requirements = self._load_csv(requirements_file)
        self.actions = self._load_json(actions_file)
        
        # Создание словарей для быстрого поиска
        self.complexity_ids = {}  # Словарь для хранения complexity из требований с разбивкой по неделям
        for req in self.requirements:
            if 'complexity' in req and req['complexity'] and 'Неделя' in req:
                week = req.get('Неделя', '')
                complexity_id = int(req['complexity'])
                if week not in self.complexity_ids:
                    self.complexity_ids[week] = []
                self.complexity_ids[week].append(complexity_id)
        
        # Получаем все complexity из требований в один список
        self.all_complexity_ids = []
        for week, ids in self.complexity_ids.items():
            self.all_complexity_ids.extend(ids)
        
        # Создаем словарь complexity_id -> row для быстрого доступа
        self.complexity_details = {}
        for req in self.requirements:
            if 'complexity' in req and req['complexity']:
                self.complexity_details[int(req['complexity'])] = req
        
        # Словарь для хранения всех actions из actions.json
        self.actions_by_id = {}
        for action_group in self.actions:
            for action in action_group:
                action_id = action.get('@id')
                if action_id:
                    self.actions_by_id[int(action_id)] = action
        
        # Словарь для хранения всех квестов из promo.json и их упражнений
        self.promo_quests = {}
        self.complexity_to_quest = {}  # Словарь для связи complexity -> quest_id
        
        for quest in self.promo.get('quests', []):
            quest_id = quest.get('id')
            if quest_id is not None:
                self.promo_quests[quest_id] = quest
                
                # Получаем список упражнений из квеста
                exercises = quest.get('exercises', {})
                complexity_list = exercises.get('list', [])
                
                # Связываем каждое упражнение с квестом
                for complexity_id in complexity_list:
                    self.complexity_to_quest[complexity_id] = quest_id
        
        # Подсчет элементов
        self.stats["complexity_ids_count"] = len(self.all_complexity_ids)
        self.stats["promo_quests_count"] = len(self.promo_quests)
        self.stats["actions_count"] = len(self.actions_by_id)
        
        self.log_info(f"Загружено {self.stats['complexity_ids_count']} заданий из таблицы требований")
        self.log_info(f"Найдено {self.stats['promo_quests_count']} квестов в промо")
        self.log_info(f"Найдено {self.stats['actions_count']} записей в файле экшенов")
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
            
    def log_check(self, complexity_id, check_name, result, expected=None, actual=None, details=None, check_tag=None):
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
            log_msg = f"[CHECK:OK] {timestamp} - Complexity {complexity_id}: {check_name}{extra_info}"
        else:
            self.stats["failed_checks"] += 1
            status = f"{self.RED}✗ ОШИБКА{self.RESET}"
            log_msg = f"[CHECK:FAIL] {timestamp} - Complexity {complexity_id}: {check_name}{extra_info}"
            
            # Добавляем ошибку в список ошибок для этого complexity_id
            if complexity_id not in self.quest_errors:
                self.quest_errors[complexity_id] = []
            
            error_details = {
                "check": check_name,
                "expected": expected,
                "actual": actual,
                "details": details,
                "tag": check_tag
            }
            self.quest_errors[complexity_id].append(error_details)
            
            # Добавляем в общий список ошибок
            error_msg = f"Complexity {complexity_id}: {check_name}"
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
                    msg = f"{status} Complexity {complexity_id}: {check_name}\n"
                    msg += f"  Ожидалось:\n{textwrap.indent(expected_str, '    ')}\n"
                    msg += f"  Получено:\n{textwrap.indent(actual_str, '    ')}"
                    if details:
                        msg += f"\n  {details}"
                    print(msg)
                else:
                    print(f"{status} Complexity {complexity_id}: {check_name}{extra_info}")
                    if details:
                        print(f"  {details}")
            else:
                print(f"{status} Complexity {complexity_id}: {check_name}")
                if details:
                    print(f"  {details}")
    
    def log_warning(self, message, complexity_id=None):
        """Логирование предупреждений"""
        self.stats["warning_checks"] += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if complexity_id is not None:
            log_msg = f"[WARNING] {timestamp} - Complexity {complexity_id}: {message}"
            display_msg = f"{self.YELLOW}[ВНИМАНИЕ]{self.RESET} Complexity {complexity_id}: {message}"
            
            # Добавляем предупреждение в список для этого complexity_id
            if complexity_id not in self.quest_errors:
                self.quest_errors[complexity_id] = []
            
            self.quest_errors[complexity_id].append({
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
    
    def log_error(self, message, complexity_id=None):
        """Логирование ошибок"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if complexity_id is not None:
            log_msg = f"[ERROR] {timestamp} - Complexity {complexity_id}: {message}"
            display_msg = f"{self.RED}[ОШИБКА]{self.RESET} Complexity {complexity_id}: {message}"
            
            # Добавляем ошибку в список для этого complexity_id
            if complexity_id not in self.quest_errors:
                self.quest_errors[complexity_id] = []
            
            self.quest_errors[complexity_id].append({
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
        # Фаза 1: Проверка наличия упражнений
        self.start_phase("ФАЗА 1: ПРОВЕРКА НАЛИЧИЯ УПРАЖНЕНИЙ")
        self.validate_complexity_in_actions()
        self.validate_complexity_in_promo()
        
        # Фаза 2: Проверка конфигурации упражнений
        self.start_phase("ФАЗА 2: ПРОВЕРКА КОНФИГУРАЦИИ УПРАЖНЕНИЙ")
        self.validate_complexity_config()
        
        # Фаза 3: Проверка конфигурации наград
        self.start_phase("ФАЗА 3: ПРОВЕРКА КОНФИГУРАЦИИ НАГРАД")
        self.validate_quest_awards()
        
        # Вывод результатов
        self.print_summary()
    
    def validate_complexity_in_actions(self):
        """Проверка наличия всех complexity из requirements в actions.json"""
        self.log_info("Проверка наличия всех complexity из requirements в файле actions.json")
        
        for complexity_id in self.all_complexity_ids:
            is_in_actions = complexity_id in self.actions_by_id
            self.log_check(
                complexity_id,
                "Наличие complexity в файле экшенов",
                is_in_actions,
                "В файле экшенов",
                "Присутствует" if is_in_actions else "Отсутствует",
                "Complexity должен присутствовать в файле экшенов",
                "COMPLEXITY_IN_ACTIONS"
            )
    
    def validate_complexity_in_promo(self):
        """Проверка наличия всех complexity из requirements в promo.json"""
        self.log_info("Проверка наличия всех complexity из requirements в списке exercises promo.json")
        
        # Собираем все complexity из промо
        promo_complexity_ids = []
        for quest in self.promo.get('quests', []):
            exercises = quest.get('exercises', {})
            complexity_list = exercises.get('list', [])
            promo_complexity_ids.extend(complexity_list)
        
        # Проверяем, что все complexity из requirements присутствуют в promo
        for complexity_id in self.all_complexity_ids:
            is_in_promo = complexity_id in promo_complexity_ids
            self.log_check(
                complexity_id,
                "Наличие complexity в списке exercises промо",
                is_in_promo,
                "В списке exercises промо",
                "Присутствует" if is_in_promo else "Отсутствует",
                "Complexity должен присутствовать в списке exercises промо",
                "COMPLEXITY_IN_PROMO"
            )
        
        # Проверяем, что все complexity из promo присутствуют в requirements
        for complexity_id in promo_complexity_ids:
            is_in_requirements = complexity_id in self.all_complexity_ids
            
            if not is_in_requirements:
                self.log_warning(
                    f"Complexity {complexity_id} присутствует в промо, но отсутствует в таблице требований",
                    complexity_id
                )
    
    def validate_complexity_config(self):
        """Проверка соответствия параметров упражнений между requirements и actions"""
        self.log_info("Проверка соответствия параметров между requirements.csv и actions.json")
        
        for complexity_id in self.all_complexity_ids:
            if complexity_id not in self.actions_by_id:
                self.log_warning(f"Complexity {complexity_id} отсутствует в файле экшенов, пропускаем проверку конфигурации", complexity_id)
                continue
            
            # Получаем детали из requirements
            req_details = self.complexity_details.get(complexity_id, {})
            
            # Получаем конфигурацию из actions.json
            action = self.actions_by_id[complexity_id]
            children = action.get('#children', [])
            
            if not children:
                self.log_warning(f"Для complexity {complexity_id} не найден блок #children в файле экшенов", complexity_id)
                continue
            
            # Берем первый элемент из #children для проверки
            config = children[0]
            
            # Проверка type
            req_type = req_details.get('type', '')
            config_type = config.get('type', '')
            
            self.log_check(
                complexity_id,
                "Соответствие типа упражнения",
                req_type.lower() == config_type.lower(),
                req_type,
                config_type,
                "Тип упражнения должен совпадать с указанным в requirements",
                "TYPE_MATCH"
            )
            
            # Проверка alias
            req_alias = req_details.get('alias', '')
            config_alias = config.get('alias', '')
            
            self.log_check(
                complexity_id,
                "Соответствие названия упражнения",
                req_alias == config_alias,
                req_alias,
                config_alias,
                "Название упражнения должно совпадать с указанным в requirements",
                "ALIAS_MATCH"
            )
            
            # Проверка minLevel
            req_min_level = req_details.get('minLevel', '')
            if req_min_level and req_min_level.isdigit():
                req_min_level = int(req_min_level)
                config_min_level = config.get('minLevel', None)
                
                if config_min_level is not None:
                    self.log_check(
                        complexity_id,
                        "Соответствие минимального уровня",
                        req_min_level == config_min_level,
                        req_min_level,
                        config_min_level,
                        "Минимальный уровень должен совпадать с указанным в requirements",
                        "MIN_LEVEL_MATCH"
                    )
            
            # Проверка maxLevel
            req_max_level = req_details.get('maxLevel', '')
            if req_max_level and req_max_level.isdigit():
                req_max_level = int(req_max_level)
                config_max_level = config.get('maxLevel', None)
                
                if config_max_level is not None:
                    self.log_check(
                        complexity_id,
                        "Соответствие максимального уровня",
                        req_max_level == config_max_level,
                        req_max_level,
                        config_max_level,
                        "Максимальный уровень должен совпадать с указанным в requirements",
                        "MAX_LEVEL_MATCH"
                    )
            
            # Проверка minValue
            req_min_value = req_details.get('minValue', '')
            if req_min_value and req_min_value.isdigit():
                req_min_value = int(req_min_value)
                config_min_value = config.get('minValue', None)
                
                if config_min_value is not None:
                    self.log_check(
                        complexity_id,
                        "Соответствие минимального значения",
                        req_min_value == config_min_value,
                        req_min_value,
                        config_min_value,
                        "Минимальное значение должно совпадать с указанным в requirements",
                        "MIN_VALUE_MATCH"
                    )
    
    def validate_quest_awards(self):
        """Проверка соответствия наград квестов между requirements и promo"""
        self.log_info("Проверка соответствия наград квестов между requirements.csv и promo.json")
        
        for complexity_id in self.all_complexity_ids:
            # Проверяем наличие complexity в promo
            if complexity_id not in self.complexity_to_quest:
                self.log_warning(f"Complexity {complexity_id} не связан с квестом в промо, пропускаем проверку наград", complexity_id)
                continue
            
            # Получаем квест из промо
            quest_id = self.complexity_to_quest[complexity_id]
            quest = self.promo_quests.get(quest_id)
            
            if not quest:
                self.log_warning(f"Для complexity {complexity_id} не найден квест с id {quest_id}", complexity_id)
                continue
            
            # Получаем награды из quest
            awards = quest.get('awards', {}).get('custom', [])
            
            # Получаем ожидаемые награды из requirements
            req_details = self.complexity_details.get(complexity_id, {})
            
            # Проверяем награду count(17909)
            req_count_17909 = req_details.get('count(17909)', '')
            if req_count_17909 and req_count_17909.isdigit():
                req_count_17909 = int(req_count_17909)
                
                # Ищем награду itemId: 17909 в awards
                award_17909_found = False
                award_17909_count = None
                
                for award in awards:
                    if award.get('itemId') == 17909:
                        award_17909_found = True
                        award_17909_count = award.get('count')
                        break
                
                # Проверяем наличие награды
                self.log_check(
                    complexity_id,
                    "Наличие награды itemId: 17909 в квесте",
                    award_17909_found,
                    "Присутствует",
                    "Присутствует" if award_17909_found else "Отсутствует",
                    "Награда itemId: 17909 должна присутствовать в квесте",
                    "AWARD_17909_PRESENCE"
                )
                
                # Проверяем количество награды
                if award_17909_found:
                    self.log_check(
                        complexity_id,
                        "Соответствие количества награды itemId: 17909",
                        req_count_17909 == award_17909_count,
                        req_count_17909,
                        award_17909_count,
                        "Количество награды должно совпадать с указанным в requirements",
                        "AWARD_17909_COUNT"
                    )
            
            # Проверяем награду count(17908)
            req_count_17908 = req_details.get('count(17908)', '')
            if req_count_17908 and req_count_17908.isdigit():
                req_count_17908 = int(req_count_17908)
                
                # Ищем награду itemId: 17908 в awards
                award_17908_found = False
                award_17908_count = None
                
                for award in awards:
                    if award.get('itemId') == 17908:
                        award_17908_found = True
                        award_17908_count = award.get('count')
                        break
                
                # Проверяем наличие награды
                self.log_check(
                    complexity_id,
                    "Наличие награды itemId: 17908 в квесте",
                    award_17908_found,
                    "Присутствует",
                    "Присутствует" if award_17908_found else "Отсутствует",
                    "Награда itemId: 17908 должна присутствовать в квесте",
                    "AWARD_17908_PRESENCE"
                )
                
                # Проверяем количество награды
                if award_17908_found:
                    self.log_check(
                        complexity_id,
                        "Соответствие количества награды itemId: 17908",
                        req_count_17908 == award_17908_count,
                        req_count_17908,
                        award_17908_count,
                        "Количество награды должно совпадать с указанным в requirements",
                        "AWARD_17908_COUNT"
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
                writer.writerow(["Complexity ID", "Проверка", "Результат", "Ожидаемое", "Фактическое", "Детали"])
                
                # Данные по ошибкам
                for complexity_id, errors in self.quest_errors.items():
                    for error in errors:
                        writer.writerow([
                            complexity_id,
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

def main():
    """Основная функция запуска валидатора"""
    parser = argparse.ArgumentParser(description='Валидатор конфигурации еженедельных квестов SeasonPass')
    parser.add_argument('--promo', default='promo.json', help='Путь к JSON-файлу с промо-акцией')
    parser.add_argument('--requirements', default='requirements.csv', help='Путь к CSV-файлу с требованиями')
    parser.add_argument('--actions', default='actions.json', help='Путь к JSON-файлу с действиями')
    parser.add_argument('--verbose', action='store_true', help='Подробное логирование')
    parser.add_argument('--json-output', action='store_true', help='Вывод в формате JSON (отключает текстовый вывод)')
    parser.add_argument('--report', default='validation_report.csv', help='Имя файла для сохранения отчета')
    parser.add_argument('--log', default='validation_detailed.log', help='Имя файла для сохранения детального лога')
    
    args = parser.parse_args()
    
    # Создаем экземпляр валидатора
    validator = QuestsValidator(
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