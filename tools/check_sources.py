#!/usr/bin/env python3
"""Проверки исходников конфигурации, которые не делает BSL Language Server.

1. Кодировка: UTF-8 с BOM и переносы CRLF во всех .bsl и .xml (так пишет Конфигуратор).
2. XML: все файлы метаданных корректно разбираются.
3. СтрШаблон: число переданных значений совпадает с максимальным номером подстановки %N
   (лишний параметр платформа не прощает: «Слишком много фактических параметров»).
4. Вызовы общих модулей и модулей менеджеров: метод существует и объявлен с Экспорт.
5. Ссылки на метаданные в коде (Справочники.X, Документ.X, ЗНАЧЕНИЕ(Перечисление.X.Y) ...)
   указывают на существующие объекты и значения перечислений.

Запуск: python3 tools/check_sources.py [каталог src]. Код возврата 1 — есть ошибки.
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

SRC = sys.argv[1] if len(sys.argv) > 1 else "src"
MD = "{http://v8.1c.ru/8.3/MDClasses}"
WORD = r"[\wА-Яа-яЁё]+"
errors = []


def error(path, message):
    errors.append("%s: %s" % (os.path.relpath(path, SRC), message))


def code_without_comments_and_strings(text):
    """Вырезает комментарии и содержимое строковых литералов (в т.ч. многострочных с |)."""
    result, in_string = [], False
    for line in text.split("\n"):
        out, i = "", 0
        if in_string:
            match = re.match(r"\s*\|", line)
            if match:
                i = match.end()
            else:
                in_string = False
        while i < len(line):
            ch = line[i]
            if in_string:
                if ch == '"':
                    if line[i + 1:i + 2] == '"':
                        i += 2
                        continue
                    in_string = False
                    out += '""'
            elif line.startswith("//", i):
                break
            elif ch == '"':
                in_string = True
            else:
                out += ch
            i += 1
        result.append(out)
    return "\n".join(result)


def call_arguments(text, open_paren):
    """Аргументы вызова верхнего уровня, начиная с открывающей скобки."""
    depth, args, current, in_string = 0, [], "", False
    for i in range(open_paren, len(text)):
        ch = text[i]
        if in_string:
            current += ch
            if ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            current += ch
        elif ch == "(":
            depth += 1
            if depth > 1:
                current += ch
        elif ch == ")":
            depth -= 1
            if depth == 0:
                args.append(current)
                return args
            current += ch
        elif ch == "," and depth == 1:
            args.append(current)
            current = ""
        else:
            current += ch
    return args


def methods(text):
    found = {}
    pattern = r"^\s*(?:Процедура|Функция)\s+(%s)\s*\([^)]*\)\s*(Экспорт)?" % WORD
    for match in re.finditer(pattern, text, re.M | re.I):
        found[match.group(1)] = bool(match.group(2))
    return found


def check_encoding(files):
    for path in files:
        data = open(path, "rb").read()
        if not data.startswith(b"\xef\xbb\xbf"):
            error(path, "нет BOM (нужна UTF-8 с BOM)")
        if data.count(b"\n") != data.count(b"\r\n"):
            error(path, "переносы строк не CRLF")


def check_xml(files):
    for path in files:
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            error(path, "некорректный XML: %s" % exc)


def check_string_templates(bsl):
    for path, text in bsl.items():
        for match in re.finditer(r"СтрШаблон\(", text):
            args = call_arguments(text, match.end() - 1)
            if not args or '"' not in args[0]:
                continue  # шаблон из переменной - статически не проверить
            numbers = [int(n) for n in re.findall(r"%(\d)", args[0])]
            expected = max(numbers) if numbers else 0
            if expected != len(args) - 1:
                line = text[:match.start()].count("\n") + 1
                error(path, "строка %d: СтрШаблон ждет %d значений, передано %d"
                      % (line, expected, len(args) - 1))


def check_calls(bsl):
    common = {}
    managers = {}
    for path, text in bsl.items():
        parts = os.path.relpath(path, SRC).split(os.sep)
        if parts[0] == "CommonModules" and parts[-1] == "Module.bsl":
            common[parts[1]] = methods(code_without_comments_and_strings(text))
        if parts[0] in ("Documents", "Catalogs") and parts[-1] == "ManagerModule.bsl":
            kind = "Документы" if parts[0] == "Documents" else "Справочники"
            managers[(kind, parts[1])] = methods(code_without_comments_and_strings(text))
    platform = {"СоздатьДокумент", "СоздатьЭлемент", "СоздатьГруппу", "ПустаяСсылка", "НайтиПоКоду",
                "НайтиПоНаименованию", "НайтиПоРеквизиту", "НайтиПоНомеру", "ПолучитьСсылку", "Выбрать"}
    for path, text in bsl.items():
        code = code_without_comments_and_strings(text)
        for match in re.finditer(r"(?<![.\wА-Яа-яЁё])(%s)\.(%s)\s*\(" % (WORD, WORD), code):
            module, method = match.groups()
            if module in common:
                if method not in common[module]:
                    error(path, "вызов несуществующего метода %s.%s" % (module, method))
                elif not common[module][method]:
                    error(path, "метод %s.%s не экспортный" % (module, method))
        for match in re.finditer(r"(Документы|Справочники)\.(%s)\.(%s)\s*\(" % (WORD, WORD), code):
            kind, name, method = match.groups()
            if method in platform:
                continue
            known = managers.get((kind, name), {})
            if method not in known:
                error(path, "вызов несуществующего метода %s.%s.%s" % (kind, name, method))
            elif not known[method]:
                error(path, "метод %s.%s.%s не экспортный" % (kind, name, method))


def check_metadata_references(bsl):
    kinds = {
        "Catalogs": ("Справочник", "Справочники"),
        "Documents": ("Документ", "Документы"),
        "AccumulationRegisters": ("РегистрНакопления", "РегистрыНакопления"),
        "InformationRegisters": ("РегистрСведений", "РегистрыСведений"),
        "Enums": ("Перечисление", "Перечисления"),
        "Constants": ("Константы",),
        "SessionParameters": ("ПараметрыСеанса",),
    }
    names, enum_values = {}, {}
    for folder, aliases in kinds.items():
        for path in glob.glob(os.path.join(SRC, folder, "*.xml")):
            obj = list(ET.parse(path).getroot())[0]
            name = obj.find(MD + "Properties/" + MD + "Name").text
            for alias in aliases:
                names.setdefault(alias, set()).add(name)
            children = obj.find(MD + "ChildObjects")
            for child in (children if children is not None else []):
                if child.tag == MD + "EnumValue":
                    enum_values.setdefault(name, set()).add(child.find(MD + "Properties/" + MD + "Name").text)
    prefixes = "|".join(sorted({a for aliases in kinds.values() for a in aliases}, key=len, reverse=True))
    for path, text in bsl.items():
        for match in re.finditer(r"(?<![\wА-Яа-яЁё.])(%s)\.(%s)(?:\.(%s))?" % (prefixes, WORD, WORD), text):
            kind, name, member = match.groups()
            if name not in names.get(kind, set()):
                error(path, "неизвестный объект метаданных %s.%s" % (kind, name))
            elif kind.startswith("Перечислени") and member and member != "ПустаяСсылка" \
                    and member not in enum_values.get(name, set()):
                error(path, "неизвестное значение перечисления %s" % match.group(0))
        for match in re.finditer(r"ЗНАЧЕНИЕ\((Перечисление)\.(%s)\.(%s)\)" % (WORD, WORD), text):
            if match.group(3) not in enum_values.get(match.group(2), set()):
                error(path, "неизвестное значение перечисления %s" % match.group(0))


def main():
    bsl_files = glob.glob(os.path.join(SRC, "**", "*.bsl"), recursive=True)
    xml_files = glob.glob(os.path.join(SRC, "**", "*.xml"), recursive=True)
    check_encoding(bsl_files + xml_files)
    check_xml(xml_files)
    bsl = {path: open(path, encoding="utf-8-sig").read().replace("\r\n", "\n") for path in bsl_files}
    check_string_templates(bsl)
    check_calls(bsl)
    check_metadata_references(bsl)

    print("Проверено файлов: %d BSL, %d XML" % (len(bsl_files), len(xml_files)))
    for message in errors:
        print("ОШИБКА " + message)
    if errors:
        print("Ошибок: %d" % len(errors))
        sys.exit(1)
    print("Ошибок нет")


if __name__ == "__main__":
    main()
