from __future__ import annotations

import sys

from isa import Instruction, Opcode, write_data_and_code
from machine_hw import DataPath


def term2instructions(symbol):
    """Отображение операторов исходного кода в коды операций."""
    return {
        "+": [Instruction(Opcode.ADD)],
        "-": [Instruction(Opcode.SUB)],
        "dup": [Instruction(Opcode.DUP)],
        "over": [Instruction(Opcode.OVER)],
        "key": [Instruction(Opcode.LIT, arg=DataPath.READ_MEM_IO_MAPPING), Instruction(Opcode.LOAD)],
        "emit": [Instruction(Opcode.LIT, arg=DataPath.WRITE_MEM_IO_MAPPING_CHAR), Instruction(Opcode.STORE)],
        ".": [Instruction(Opcode.LIT, arg=DataPath.WRITE_MEM_IO_MAPPING_INT), Instruction(Opcode.STORE)],
        "!": [Instruction(Opcode.STORE)],
        "@": [Instruction(Opcode.LOAD)],
        "<": [Instruction(Opcode.SUB), Instruction(Opcode.ISNEG)],
        ">": [Instruction(Opcode.SUB), Instruction(Opcode.NEG), Instruction(Opcode.ISNEG)],
        "=": [Instruction(Opcode.SUB), Instruction(Opcode.INV)],
        "or": [Instruction(Opcode.OR)],
        "and": [Instruction(Opcode.AND)],
        "invert": [Instruction(Opcode.INV)],
    }.get(symbol, None)


def check_balance_in_terms(terms: list[str]):
    """Проверяет закрыты ли условные операторы, операторы циклов, определения процедур"""
    # но вообще надо проверять на "правильную скобочную последовательность"

    pairs_to_check = [("begin", "until"), ("if", "then"), (":", ";")]

    stack = []
    for term in terms:
        if term in ("begin", "if", ":"):
            assert term != ":" or ":" not in stack, "Sub-functions not allowed"
            stack.append(term)
        if term in ("until", "then", ";"):
            assert len(stack) >= 1, "Unbalanced pairs."
            t = stack.pop()
            assert (t, term) in pairs_to_check, f"Unbalanced pairs. ({t} - {term})!"
    assert len(stack) == 0, "Unbalanced pairs."


def remove_brackets(terms: list[str]):
    """Убирает то, что в скобах (например семантика функции)"""
    new_terms = []
    deep = 0
    for term_num, term in enumerate(terms):
        if term[0] == "(":
            deep += 1
        if deep == 0:
            new_terms.append(term)
        if term[-1] == ")":
            deep -= 1
    assert deep == 0, "Unbalanced ()!"
    return new_terms


def split_with_saving_string_literals(text: str):
    """Разбивает на токены, причем ." " тоже считается токеном."""
    string_literals = []
    text_prep = [text]
    while isinstance(text_prep[-1], str) and text_prep[-1].find('."'):
        left = text_prep[-1].find('."')
        right = text_prep[-1].find('"', left + 2)
        if left != -1 and right != -1:
            string_literals.append(text_prep[-1][left : right + 1])
            raw = text_prep.pop()
            text_prep.append(raw[0:left].split())
            text_prep.append(raw[right + 1 : :])
        else:
            text_prep.append(text_prep.pop().split())
    if isinstance(text_prep[-1], str):
        raw = text_prep.pop()
        text_prep.append(raw.split())

    terms = []
    for i in range(len(text_prep) - 1):
        terms += text_prep[i]
        terms.append(string_literals[i])
    terms += text_prep[-1]

    return terms


def remove_comments(text: str):
    """Убирает все в строке после /"""
    result = []
    skip = False

    for char in text:
        if char == "/":
            skip = True
        elif char == "\n":
            skip = False
            result.append(char)
        if not skip:
            result.append(char)

    return "".join(result)


def text2terms(text) -> list[str]:
    """Трансляция текста в последовательность операторов языка (токенов).

    Включает в себя:

    - отсеивание всех незначимых символов (считаются комментариями);
    - проверка формальной корректности программы (парность оператора цикла).
    """
    text = remove_comments(text)
    terms = split_with_saving_string_literals(text)
    check_balance_in_terms(terms)
    return remove_brackets(terms)


def find_variables(terms: list[str]):
    """Находим токены, определяющие переменные, и даем им место в памяти"""
    variables: dict[str, int] = dict()
    # Память в модели не ограничивается, поэтому можно выделять память после ячеек предназначенных под порты
    last_free_address = (
        max(DataPath.READ_MEM_IO_MAPPING, DataPath.WRITE_MEM_IO_MAPPING_INT, DataPath.WRITE_MEM_IO_MAPPING_CHAR) + 1
    )

    # Получается формально ничего не мешает объявить переменную где угодно. Но она, очевидно, глобальная
    for i in range(len(terms) - 3):
        if terms[i] == "variable":
            variables[terms[i + 1]] = last_free_address
            last_free_address += 1
            if terms[i + 3] == "allot":
                last_free_address += int(terms[i + 2])

    if terms[-2] == "variable":
        variables[terms[-1]] = last_free_address
        last_free_address += 1

    return variables, last_free_address


def remove_term_var(terms: list[str]):
    while "variable" in terms:
        i = terms.index("variable")
        terms = terms[0:i:] + terms[i + 2 : :]
    while "allot" in terms:
        i = terms.index("allot")
        terms = terms[0 : i - 1 :] + terms[i + 1 : :]
    return terms


def find_functions(terms: list[str]):
    """Определяем имена функций"""
    functions: set[str] = set()

    for i in range(len(terms) - 1):
        if terms[i] == ":":
            functions.add(terms[i + 1])

    return functions


def translate(text):  # noqa: C901
    terms = text2terms(text)
    variables, last_free_address = find_variables(terms)
    terms = remove_term_var(terms)
    functions = find_functions(terms)

    data: list[int | str] = [0] * last_free_address  # инициализируем выделенную память
    code: list[Instruction] = []

    # Транслируем термы в машинный код.
    terms_to_instruction_lists: list[list[Instruction]] = []
    jmp_stack: list[int] = []
    func_addr: dict[str, int] = dict()
    for term_num in range(len(terms)):
        if terms[term_num] == "begin":
            # оставляем placeholder, который будет заменён в конце цикла
            terms_to_instruction_lists.append([None])
            jmp_stack.append(len(terms_to_instruction_lists) - 1)
        elif terms[term_num] == "until":
            # формируем цикл с началом из jmp_stack
            begin_pc = jmp_stack.pop()
            begin = Instruction(Opcode.NOP)
            end = [Instruction(Opcode.INV), Instruction(Opcode.JNZ, begin_pc)]
            terms_to_instruction_lists[begin_pc] = [begin]
            terms_to_instruction_lists.append(end)

        elif terms[term_num] == "if":
            terms_to_instruction_lists.append([None])
            jmp_stack.append(len(terms_to_instruction_lists) - 1)
        elif terms[term_num] == "then":
            terms_to_instruction_lists.append([Instruction(Opcode.NOP)])
            terms_to_instruction_lists[jmp_stack.pop()] = [
                Instruction(Opcode.INV),
                Instruction(Opcode.JNZ, len(terms_to_instruction_lists)),
            ]

        elif term2instructions(terms[term_num]) is not None:  # Обработка тривиально отображаемых операций
            terms_to_instruction_lists.append(term2instructions(terms[term_num]))

        elif terms[term_num] in variables:
            # обращение к переменной - положить ассоциированный адрес на вершину стека
            terms_to_instruction_lists.append([Instruction(Opcode.LIT, arg=variables[terms[term_num]])])
        elif terms[term_num] == "+!":
            terms_to_instruction_lists.append(
                [
                    Instruction(Opcode.LOAD),
                    Instruction(Opcode.ADD),
                    Instruction(Opcode.LIT, arg=variables[terms[term_num - 1]]),  # адрес переменной
                    Instruction(Opcode.STORE),
                ]
            )

        elif terms[term_num] == ":":  # если пришли к определению функции, то её надо перепрыгнуть
            terms_to_instruction_lists.append([None])
            # нужно будет поставить JUMP с переходом сразу за функцию
            jmp_stack.append(len(terms_to_instruction_lists) - 1)
        elif terms[term_num] in functions:
            if terms[term_num - 1] != ":":
                terms_to_instruction_lists.append([Instruction(Opcode.CALL, arg=func_addr[terms[term_num]])])
            else:
                # записываем номер терма с началом функции (указываем на NOP)
                func_addr[terms[term_num]] = term_num
                # чтобы не ломать адресацию замещаем токен с именем функции на NOP
                terms_to_instruction_lists.append([Instruction(Opcode.NOP)])
        elif terms[term_num] == ";":
            terms_to_instruction_lists.append([Instruction(Opcode.RET)])
            terms_to_instruction_lists[jmp_stack.pop()] = [Instruction(Opcode.JMP, len(terms_to_instruction_lists))]

        elif terms[term_num][0:2:] == '."' and terms[term_num][-1] == '"':
            # Записываем строку в память по одному символу на ячейку. Причем храним Unicode коды.
            data += [ord(char) for char in terms[term_num][2:-1:]]
            # Инициализация указателя на ячейку памяти отдельным токеном
            # (чтобы при смене номеров токенов в аргументах на адреса инструкций не трогать эту инструкцию)
            terms_to_instruction_lists.append([Instruction(Opcode.LIT, arg=len(data) - len(terms[term_num][2:-1:]))])

            # цикл вывода строки
            terms_to_instruction_lists.append(
                [
                    Instruction(Opcode.DUP),
                    Instruction(Opcode.LOAD),
                    Instruction(Opcode.LIT, arg=DataPath.WRITE_MEM_IO_MAPPING_CHAR),
                    Instruction(Opcode.STORE),
                    # инкремент адреса памяти
                    Instruction(Opcode.LIT, arg=1),
                    Instruction(Opcode.ADD),
                    # <
                    Instruction(Opcode.DUP),
                    Instruction(Opcode.LIT, arg=len(data)),
                    Instruction(Opcode.SUB),
                    Instruction(Opcode.ISNEG),
                    Instruction(Opcode.JNZ, arg=len(terms_to_instruction_lists)),
                ]
            )
        elif terms[term_num].isdigit() or terms[term_num][0] == "-" and terms[term_num][1::].isdigit():
            terms_to_instruction_lists.append([Instruction(Opcode.LIT, arg=int(terms[term_num]))])
        else:
            pass

    for term_num in range(len(terms_to_instruction_lists)):
        code += terms_to_instruction_lists[term_num]

    # В машинном коде инструкций больше, чем токенов. Обновляем аргумент
    for c in range(len(code)):
        if code[c].opcode in (Opcode.CALL, Opcode.JMP, Opcode.JNZ):
            term_num = code[c].arg
            pc = sum([len(i) for i in terms_to_instruction_lists[0:term_num]])
            code[c].arg = pc

    # Добавляем инструкцию остановки процессора в конец программы.
    code.append(Instruction(Opcode.HALT))
    return data, code


def main(source, target):
    """Функция запуска транслятора. Параметры -- исходный и целевой файлы."""
    with open(source, encoding="utf-8") as f:
        source = f.read()

    data, code = translate(source)

    write_data_and_code(target, data, code)
    print("source LoC:", len(source.split("\n")), "code instr:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
