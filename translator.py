import sys

from isa import Opcode, Term, write_code


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


def text2terms(text):
    """Трансляция текста в последовательность операторов языка (токенов).

    Включает в себя:

    - отсеивание всех незначимых символов (считаются комментариями);
    - проверка формальной корректности программы (парность оператора цикла).
    """
    terms = []
    for line_num, line in enumerate(text.split(), 1):
        # TODO '()'
        terms.append(Term(line_num, line))

    deep = 0
    for term in terms:
        if term.symbol == "begin":
            deep += 1
        if term.symbol == "until":
            deep -= 1
        assert deep >= 0, "Unbalanced begin-until!"
    assert deep == 0, "Unbalanced begin-until!"

    deep = 0
    for term in terms:
        if term.symbol == "if":
            deep += 1
        if term.symbol == "then":
            deep -= 1
        assert deep >= 0, "Unbalanced if-then!"
    assert deep == 0, "Unbalanced if-then!"

    return terms


def translate(text):
    """Трансляция текста программы в машинный код.

    Выполняется в два этапа:

    1. Трансляция текста в последовательность операторов языка (токенов).

    2. Генерация машинного кода.

        - Прямое отображение части операторов в машинный код.

        - Отображение операторов цикла в инструкции перехода с учётом
    вложенности и адресации инструкций. Подробнее см. в документации к
    `isa.Opcode`.

    """
    terms = text2terms(text)

    # Транслируем термы в машинный код.
    code = []
    jmp_stack = []
    for pc, term in enumerate(terms):
        if term.symbol == "begin":
            # оставляем placeholder, который будет заменён в конце цикла
            code.append(None)
            jmp_stack.append(pc)
        elif term.symbol == "until":
            # формируем цикл с началом из jmp_stack
            begin_pc = jmp_stack.pop()
            begin = {"index": pc, "opcode": Opcode.JZ, "arg": pc + 1, "term": terms[begin_pc]}
            end = {"index": pc, "opcode": Opcode.JMP, "arg": begin_pc, "term": term}
            code[begin_pc] = begin
            code.append(end)
        elif term.symbol == "if":
            pass
        elif term.symbol == "then":
            pass
        else:
            inst = term2instructions(term.symbol)
            # Обработка тривиально отображаемых операций.
            # code.append({"index": pc, "opcode": symbol2opcode(term.symbol), "term": term})

    # Добавляем инструкцию остановки процессора в конец программы.
    code.append({"index": len(code), "opcode": Opcode.HALT})
    return code


def main(source, target):
    """Функция запуска транслятора. Параметры -- исходный и целевой файлы."""
    with open(source, encoding="utf-8") as f:
        source = f.read()

    code = translate(source)

    write_code(target, code)
    print("source LoC:", len(source.split("\n")), "code instr:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)