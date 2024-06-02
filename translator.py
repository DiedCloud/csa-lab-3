import sys

from isa import Opcode, Instruction, write_data_and_code


def term2instructions(symbol):
    """Отображение операторов исходного кода в коды операций."""
    return {
        "+": [Opcode.ADD],
        "-": [Opcode.SUB],
        ";": [Opcode.RET],
        "dup": [Opcode.DUP],
        "over": [Opcode.OVER],
        "key": [Opcode.LIT, Opcode.LOAD],
        "emit": [Opcode.LIT, Opcode.STORE],
        ".": [Opcode.LIT, Opcode.STORE],
        "!": [Opcode.STORE],
        "@": [Opcode.LOAD],
        "<": [Opcode.SUB, Opcode.ISNEG],
        ">": [Opcode.SUB, Opcode.NEG, Opcode.ISNEG],
        "=": [Opcode.SUB, Opcode.INV],
        "or": [Opcode.OR],
        "and": [Opcode.AND],
        "invert": [Opcode.INV],
        # "if": [Opcode.JZ],
        "+!": [Opcode.LOAD, Opcode.ADD, Opcode.LIT, Opcode.STORE], # LIT нужен для повторной загрузки адреса переменной
    }.get(symbol, None)


def check_balance_in_terms(terms: list[str]):
    # но вообще надо проверять на "правильную скобочную последовательность"

    deep = 0
    for term in terms:
        if term == "begin":
            deep += 1
        if term == "until":
            deep -= 1
        assert deep >= 0, "Unbalanced begin-until!"
        assert deep <= 1, "Sub-functions not allowed"
    assert deep == 0, "Unbalanced begin-until!"

    deep = 0
    for term in terms:
        if term == "if":
            deep += 1
        if term == "then":
            deep -= 1
        assert deep >= 0, "Unbalanced if-then!"
    assert deep == 0, "Unbalanced if-then!"

    deep = 0
    for term in terms:
        if term == ":":
            deep += 1
        if term == ";":
            deep -= 1
        assert deep >= 0, "Unbalanced :;!"
    assert deep == 0, "Unbalanced :;!"


def remove_brackets(terms: list[str]):
    # убираем то, что в скобах (например семантика функции)
    new_terms = []
    deep = 0
    for term_num, term in enumerate(terms):
        if term == "(":
            deep += 1
        if term == ")":
            deep -= 1
        assert deep >= 0, "Unbalanced ()!"
        if deep == 0:
            new_terms.append(term)
    assert deep == 0, "Unbalanced ()!"
    return new_terms


def split_with_saving_string_literals(text: str):
    string_literals = []
    text_prep = [text]
    while isinstance(text_prep[-1], str) and text_prep[-1].find(".\""):
        left = text_prep[-1].find(".\"")
        right = text_prep[-1].find("\"", left+2)
        if left != -1 and right != -1:
            string_literals.append(text_prep[-1][left:right+1])
            raw = text_prep.pop()
            text_prep.append(raw[0:left].split())
            text_prep.append(raw[right+1::])
        else:
            text_prep.append(text_prep.pop().split())
    if isinstance(text_prep[-1], str):
        raw = text_prep.pop()
        text_prep.append(raw.split())

    terms = []
    i = 0
    for i in range(len(text_prep)-1):
        terms += text_prep[i]
        terms.append(string_literals[i])
    terms += text_prep[-1]

    return terms


def text2terms(text) -> list[str]:
    """Трансляция текста в последовательность операторов языка (токенов).

    Включает в себя:

    - отсеивание всех незначимых символов (считаются комментариями);
    - проверка формальной корректности программы (парность оператора цикла).
    """
    terms = split_with_saving_string_literals(text)
    check_balance_in_terms(terms)
    terms = remove_brackets(terms)
    return terms


def find_variables(terms: list[str]):
    """Находим токены, определяющие переменные, и даем им место в памяти"""
    variables: dict[str, int] = dict()
    last_free_address = 0

    # Получается формально ничего не мешает объявить переменную где угодно. Но она, очевидно, глобальная
    for i in range(len(terms)-3):
        if terms[i] == "variable":
            variables[terms[i+1]] = last_free_address
            last_free_address += 1
            if terms[i+3] == "allot":
                last_free_address += int(terms[i+2])

    if terms[-2] == "variable":
        variables[terms[-1]] = last_free_address
        last_free_address += 1

    return variables, last_free_address


def remove_term_var(terms: list[str]):
    while "variable" in terms:
        terms.remove("variable")
    return terms


def find_functions(terms: list[str]):
    """Определяем номера токенов начал функций"""
    functions: dict[str, tuple[int, int]] = dict()

    begin = 0
    for i in range(len(terms)-1):
        if terms[i] == ":":
            begin = i + 1 # Сразу в начало кода функции. (скобки убраны из токенов)
        if terms[i] == ";":
            functions[terms[begin]] = (begin, i + 1) # Сразу в после кода функции, т.к. ; это инструкция ret

    return functions


def translate(text):
    terms = text2terms(text)
    variables, last_free_address = find_variables(terms)
    terms = remove_term_var(terms)
    functions = find_functions(terms)

    data: list[int | str] = [0] * last_free_address # инициализируем выделенную память
    code: list[Instruction] = []

    # Транслируем термы в машинный код.
    terms_to_instruction_lists: list[list[Instruction]] = []
    jmp_stack: list[int] = []
    for term_num in range(len(terms)):

        if terms[term_num] == "begin":
            # оставляем placeholder, который будет заменён в конце цикла
            terms_to_instruction_lists.append([None])
            jmp_stack.append(len(terms_to_instruction_lists)-1)
        elif terms[term_num] == "until":
            # формируем цикл с началом из jmp_stack
            begin_pc = jmp_stack.pop()
            begin = Instruction(Opcode.NOP)
            end = Instruction(Opcode.JZ, begin_pc)
            terms_to_instruction_lists[begin_pc] = [begin]
            terms_to_instruction_lists.append([end])

        elif terms[term_num] == "if":
            terms_to_instruction_lists.append([None])
            jmp_stack.append(len(terms_to_instruction_lists)-1)
        elif terms[term_num] == "then":
            terms_to_instruction_lists[jmp_stack.pop()] = [Instruction(Opcode.JZ, len(terms_to_instruction_lists))]
            terms_to_instruction_lists.append([Instruction(Opcode.NOP)])

        elif term2instructions(terms[term_num]) is not None: # Обработка тривиально отображаемых операций.
            opcodes: list[Opcode] = term2instructions(terms[term_num])
            instructions: list[Instruction] = []
            for op in opcodes:
                if op == Opcode.LIT: # ПЛОХО. Но аргументы имеют только LIT и прыжки, а в ответе может быть только LIT, которому нужна 1
                    instructions.append(Instruction(op, arg=1))
                else:
                    instructions.append(Instruction(op))
            terms_to_instruction_lists.append(instructions)

        elif terms[term_num] in variables:
            # обращение к переменной - положить ассоциированный адрес на вершину стека
            terms_to_instruction_lists.append([Instruction(Opcode.LIT, arg=variables[terms[term_num]])])

        elif terms[term_num] == ":":  # если пришли к определению функции, то её надо перепрыгнуть
            terms_to_instruction_lists.append([Instruction(Opcode.JMP, arg=functions[terms[term_num+1]][1])])
        elif terms[term_num] in functions:
            if terms[term_num-1] != ":":
                terms_to_instruction_lists.append([Instruction(Opcode.CALL, arg=functions[terms[term_num]][0])])

        elif terms[term_num][0:2:] == ".\"" and terms[term_num][-1] == "\"":
            data += [char for char in terms[term_num][2:-1:]]
            terms_to_instruction_lists.append([
                Instruction(Opcode.LIT, arg=len(data)-len(terms[term_num][2:-1:])),

                Instruction(Opcode.LIT, arg=0), # TODO порт вывода
                Instruction(Opcode.OVER),
                Instruction(Opcode.LOAD),
                Instruction(Opcode.STORE),

                Instruction(Opcode.LIT, arg=1),
                Instruction(Opcode.ADD), # инкремент адреса памяти

                Instruction(Opcode.DUP),
                Instruction(Opcode.SUB), # <
                Instruction(Opcode.ISNEG),
                Instruction(Opcode.JZ, arg=term_num) # term_num+1 т.к. цикл начинается на второй инструкции из этих
            ])
        elif terms[term_num].isdigit() or terms[term_num][0] == '-' and terms[term_num][1::].isdigit():
            terms_to_instruction_lists.append([Instruction(Opcode.LIT, arg=int(terms[term_num]))])
        else:
            pass

    cur_pc = 0
    print(terms_to_instruction_lists)
    for term_num in range(len(terms_to_instruction_lists)):
        i = term_num + 1
        while i < len(terms_to_instruction_lists):
            if terms_to_instruction_lists[i][0].arg == term_num: # если есть вызовы с таким номером токена
                terms_to_instruction_lists[i][0].arg = cur_pc  # то поставить им правильный адрес
            i += 1
        code += terms_to_instruction_lists[term_num]
        cur_pc += len(terms_to_instruction_lists[term_num])

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
    # assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    # _, source, target = sys.argv
    main("algorithms/prob1.fth", "prob1.json")
