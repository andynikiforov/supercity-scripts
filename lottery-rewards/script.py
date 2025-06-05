#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Скрипт для проверки лотереи в SeasonPass

import json
import csv
import os
import sys
import argparse
from datetime import datetime
import textwrap

class LotteryRewardsValidator:
    def __init__(self, promo_file="promo.json", requirements_file="requirements.csv", 
                 actions_file="actions.json", verbose=True, json_output=False):
        """
        Инициализация валидатора конфигурации лотереи SeasonPass.
        
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
            "warning_checks": 0
        }
        
        # Текущая фаза проверки
        self.current_phase = ""
        
        # Ошибки для сводной таблицы
        self.config_errors = {}
        
        self.print_header("ВАЛИДАЦИЯ КОНФИГУРАЦИИ ЛОТЕРЕИ SEASONPASS")
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
        
        # Группировка требований по ID экшенов
        self.requirements_by_action_id = {}
        current_action_id = None
        current_group = []
        
        for req in self.requirements:
            action_id = req.get('action', '').strip()
            if action_id:  # Новая группа
                if current_action_id:  # Сохраняем предыдущую группу
                    self.requirements_by_action_id[current_action_id] = current_group
                current_action_id = action_id
                current_group = [req]
            else:  # Продолжение текущей группы
                if current_action_id:  # Если есть текущая группа
                    current_group.append(req)
        
        # Сохраняем последнюю группу
        if current_action_id and current_group:
            self.requirements_by_action_id[current_action_id] = current_group
            
        # Создание словаря для быстрого поиска экшенов по ID
        self.actions_by_id = {}
        for action in self.actions:
            action_id = action.get('@id')
            if action_id:
                self.actions_by_id[str(action_id)] = action
        
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
            
    def log_check(self, check_name, result, expected=None, actual=None, details=None, check_id=None):
        """Логирование результата проверки"""
        self.stats["total_checks"] += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if result:
            self.stats["passed_checks"] += 1
            status = f"{self.GREEN}✓ УСПЕХ{self.RESET}"
            log_msg = f"[CHECK:OK] {timestamp} - {check_name}"
            if expected is not None and actual is not None:
                log_msg += f" (ожидалось: {expected}, фактически: {actual})"
        else:
            self.stats["failed_checks"] += 1
            status = f"{self.RED}✗ ОШИБКА{self.RESET}"
            log_msg = f"[CHECK:FAIL] {timestamp} - {check_name}"
            if expected is not None and actual is not None:
                log_msg += f" (ожидалось: {expected}, фактически: {actual})"
            
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
        
        if self.verbose:
            check_text = check_name
            if expected is not None and actual is not None:
                if result:
                    value_text = f"{self.GREEN}[{actual}]{self.RESET}"
                else:
                    value_text = f"{self.RED}[получено: {actual}, ожидалось: {expected}]{self.RESET}"
                check_text += f" {value_text}"
            
            # Показываем детали только если тест не прошел
            if not result and details:
                check_text += f"\n    {self.YELLOW}Детали: {details}{self.RESET}"
                
            print(f"{status} {check_text}")
            
    def log_warning(self, message, check_id=None):
        """Логирование предупреждений"""
        self.stats["warning_checks"] += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[WARNING] {timestamp} - {message}"
        self.warnings.append(message)
        self.info_logs.append(log_entry)
        
        if check_id is not None:
            if check_id not in self.config_errors:
                self.config_errors[check_id] = []
            self.config_errors[check_id].append({"check": "Предупреждение", "details": message})
        
        if self.verbose:
            print(f"{self.YELLOW}[ПРЕДУПРЕЖДЕНИЕ]{self.RESET} {message}")
            
    def log_error(self, message, check_id=None):
        """Логирование ошибок"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[ERROR] {timestamp} - {message}"
        self.errors.append(message)
        self.info_logs.append(log_entry)
        
        if check_id is not None:
            if check_id not in self.config_errors:
                self.config_errors[check_id] = []
            self.config_errors[check_id].append({"check": "Ошибка", "details": message})
        
        if self.verbose:
            print(f"{self.RED}[ОШИБКА]{self.RESET} {message}")
    
    def start_phase(self, phase_name):
        """Начало новой фазы проверки"""
        self.current_phase = phase_name
        self.print_header(f"ФАЗА: {phase_name}")
        
    def validate_all(self):
        """Выполнение всех проверок"""
        self.start_phase("Проверка наличия экшенов в промо и конфиге")
        self.validate_actions_presence()
        
        self.start_phase("Проверка наполнения экшенов")
        self.validate_actions_content()
        
        self.start_phase("Проверка параметра needAction")
        self.validate_need_action()
        
        self.print_summary()
        
    def validate_actions_presence(self):
        """Проверка наличия всех требуемых экшенов в промо и конфиге"""
        # Получаем список ID экшенов из требований
        action_ids = list(self.requirements_by_action_id.keys())
        self.log_info(f"Найдено {len(action_ids)} экшенов в требованиях: {', '.join(action_ids)}")
        
        # Проверяем наличие в промо
        for action_id in action_ids:
            promo_actions = [str(award) for award in self.promo.get("awards", [])]
            self.log_check(
                f"Экшен {action_id} присутствует в промо (awards)",
                action_id in promo_actions,
                expected="присутствует",
                actual="присутствует" if action_id in promo_actions else "отсутствует",
                check_id=action_id
            )
        
        # Проверяем наличие в конфиге экшенов
        for action_id in action_ids:
            self.log_check(
                f"Экшен {action_id} присутствует в конфиге экшенов",
                action_id in self.actions_by_id,
                expected="присутствует",
                actual="присутствует" if action_id in self.actions_by_id else "отсутствует",
                check_id=action_id
            )
    
    def validate_actions_content(self):
        """Проверка соответствия наполнения экшенов"""
        for action_id, requirements in self.requirements_by_action_id.items():
            if action_id not in self.actions_by_id:
                self.log_error(f"Невозможно проверить наполнение экшена {action_id}, так как он отсутствует в конфиге", check_id=action_id)
                continue
                
            self.log_info(f"Проверка наполнения для экшена {action_id}")
            action_config = self.actions_by_id[action_id]
            
            # Проверяем наличие awardPackets в конфиге
            award_packets = action_config.get("awardPackets", [])
            if not award_packets:
                self.log_error(f"В конфиге для экшена {action_id} отсутствуют пакеты наград (awardPackets)", check_id=action_id)
                continue
            
            # Логируем все пакеты наград для справки
            self.log_info(f"Найдено {len(award_packets)} пакетов наград для экшена {action_id}")
            for i, packet in enumerate(award_packets):
                packet_prob = packet.get("probability", "")
                packet_alias = packet.get("alias", "")
                awards_str = []
                for award in packet.get("awards", []):
                    award_type = award.get("type", "")
                    award_count = award.get("count", "")
                    award_item_id = award.get("itemId", "")
                    award_info = f"[{award_type}"
                    if award_count:
                        award_info += f", {award_count}"
                    if award_item_id:
                        award_info += f", ID:{award_item_id}"
                    award_info += "]"
                    awards_str.append(award_info)
                
                self.log_info(f"  Пакет #{i+1}: prob={packet_prob}, alias={packet_alias}, награды: {', '.join(awards_str)}")
                
            # Для каждого требования проверяем соответствие в конфиге
            for req in requirements:
                item_type = req.get("type", "")
                count = req.get("count", "")
                item_id = req.get("itemId", "")
                probability = req.get("probability", "")
                alias = req.get("alias", "")  # Используем только для отображения
                
                # Ищем соответствующий пакет в конфиге
                found_packet = False
                for packet in award_packets:
                    packet_probability = str(packet.get("probability", ""))
                    awards = packet.get("awards", [])
                    
                    if packet_probability == probability:
                        # Нашли пакет с такой же вероятностью, теперь проверяем награды
                        for award in awards:
                            award_type = award.get("type", "")
                            award_count = str(award.get("count", ""))
                            
                            # Для разных типов наград используются разные поля для ID
                            # Для наград типа "buff" используется поле "id", для остальных "itemId"
                            if award_type.lower() == "buff":
                                award_item_id = str(award.get("id", ""))
                            else:
                                award_item_id = str(award.get("itemId", ""))
                            
                            # Проверяем соответствие типа (регистронезависимое), количества и itemId
                            type_match = not item_type or award_type.lower() == item_type.lower()
                            count_match = not count or award_count == count
                            item_id_match = not item_id or award_item_id == item_id
                            
                            if type_match and count_match and item_id_match:
                                found_packet = True
                                break
                        
                        if found_packet:
                            break
                
                # Используем награду с типом или идентификатором для отображения
                reward_display = ""
                if item_type:
                    reward_display = f"типа {item_type}"
                if item_id:
                    if reward_display:
                        reward_display += f" с ID {item_id}"
                    else:
                        reward_display = f"с ID {item_id}"
                if count:
                    if reward_display:
                        reward_display += f" в количестве {count}"
                    else:
                        reward_display = f"в количестве {count}"
                
                check_msg = f"Награда {reward_display} в экшене {action_id} с вероятностью {probability}%"
                details = f"type={item_type}, count={count}, itemId={item_id}, probability={probability}"
                    
                self.log_check(
                    check_msg,
                    found_packet,
                    expected="найдена",
                    actual="найдена" if found_packet else "не найдена",
                    details=details,
                    check_id=action_id
                )
    
    def validate_need_action(self):
        """Проверка параметра needAction для экшенов лотереи"""
        if not self.season_pass_actions:
            self.log_warning("Невозможно проверить параметр needAction: не найдены ID сезонного пропуска")
            return
            
        for action_id in self.requirements_by_action_id.keys():
            if action_id not in self.actions_by_id:
                self.log_error(f"Невозможно проверить параметр needAction для экшена {action_id}, так как он отсутствует в конфиге", check_id=action_id)
                continue
                
            action_config = self.actions_by_id[action_id]
            need_action = action_config.get("needAction", "")
            
            # Проверяем наличие параметра needAction
            self.log_check(
                f"Наличие параметра needAction в экшене {action_id}",
                bool(need_action),
                expected="Присутствует",
                actual="Присутствует" if need_action else "Отсутствует",
                check_id=action_id
            )
            
            if not need_action:
                continue
                
            # Проверяем соответствие needAction и seasonPassActions
            self.log_check(
                f"Параметр needAction в экшене {action_id} соответствует ID сезонного пропуска",
                need_action == self.season_pass_actions,
                expected=self.season_pass_actions,
                actual=need_action,
                check_id=action_id
            )
    
    def print_summary(self):
        """Вывод сводной информации о результатах проверки"""
        self.print_header("РЕЗУЛЬТАТЫ ПРОВЕРКИ")
        
        # Статистика
        total = self.stats["total_checks"]
        passed = self.stats["passed_checks"]
        failed = self.stats["failed_checks"]
        warnings = self.stats["warning_checks"]
        
        if self.json_output:
            return
        
        print(f"{self.BOLD}Статистика проверок:{self.RESET}")
        print(f"Всего проверок: {total}")
        print(f"{self.GREEN}Успешно: {passed} ({passed/total*100:.1f}%){self.RESET}")
        print(f"{self.RED}Неудачно: {failed} ({failed/total*100:.1f}%){self.RESET}")
        print(f"{self.YELLOW}Предупреждений: {warnings}{self.RESET}")
        
        # Если есть ошибки, показываем их
        if self.errors:
            print(f"\n{self.BOLD}{self.RED}Найдены ошибки:{self.RESET}")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
                
        # Если есть предупреждения, показываем их
        if self.warnings:
            print(f"\n{self.BOLD}{self.YELLOW}Предупреждения:{self.RESET}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")
        
        # Общий результат
        if failed == 0 and warnings == 0:
            print(f"\n{self.GREEN}{self.BOLD}Проверка пройдена успешно! ✓{self.RESET}")
        elif failed == 0:
            print(f"\n{self.YELLOW}{self.BOLD}Проверка пройдена с предупреждениями! ⚠{self.RESET}")
        else:
            print(f"\n{self.RED}{self.BOLD}Проверка не пройдена! ✗{self.RESET}")
    
    def save_report_to_csv(self, output_file="validation_report.csv"):
        """Сохранение отчета о проверке в CSV"""
        try:
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Action ID", "Проверка", "Результат", "Ожидаемое", "Фактическое", "Детали"])
                
                for check_id, errors in self.config_errors.items():
                    for error in errors:
                        writer.writerow([
                            check_id,
                            error.get("check", ""),
                            "Ошибка",
                            error.get("expected", ""),
                            error.get("actual", ""),
                            self._get_error_details(error)
                        ])
                        
            self.log_info(f"Отчет сохранен в {output_file}")
        except Exception as e:
            self.log_error(f"Ошибка при сохранении отчета: {str(e)}")
    
    def _get_error_details(self, error):
        """Формирование подробного описания ошибки"""
        check_name = error.get("check", "")
        if "Награда" in check_name:
            return f"Награда должна соответствовать требованиям"
        elif "Экшен" in check_name:
            return f"Экшен должен присутствовать в конфиге"
        else:
            return error.get("details", "")
    
    def save_detailed_log(self, output_file="validation_detailed.log"):
        """Сохранение детального лога в файл"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for log_entry in self.info_logs:
                    f.write(log_entry + "\n")
                    
            self.log_info(f"Детальный лог сохранен в {output_file}")
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
    parser = argparse.ArgumentParser(description="Валидация конфигурации лотереи SeasonPass")
    parser.add_argument("-p", "--promo", default="promo.json", help="Путь к файлу промо")
    parser.add_argument("-r", "--requirements", default="requirements.csv", help="Путь к файлу с требованиями")
    parser.add_argument("-a", "--actions", default="actions.json", help="Путь к файлу с экшенами")
    parser.add_argument("-o", "--output", default="validation_report.csv", help="Имя файла для сохранения отчета CSV")
    parser.add_argument("-l", "--log", default="validation_detailed.log", help="Имя файла для сохранения детального лога")
    parser.add_argument("-q", "--quiet", action="store_true", help="Минимальный вывод")
    parser.add_argument("-j", "--json", action="store_true", help="Вывод в JSON формате")
    args = parser.parse_args()

    validator = LotteryRewardsValidator(
        promo_file=args.promo,
        requirements_file=args.requirements,
        actions_file=args.actions,
        verbose=not args.quiet,
        json_output=args.json
    )
    
    validator.validate_all()
    
    # Всегда сохраняем отчеты
    validator.save_report_to_csv(args.output)
    validator.save_detailed_log(args.log)
    
    # Возвращаем код ошибки, если проверка не пройдена
    sys.exit(1 if validator.stats["failed_checks"] > 0 else 0)

if __name__ == "__main__":
    main() 