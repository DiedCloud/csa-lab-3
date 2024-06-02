"""Представление исходного и машинного кода.

Особенности реализации:

- Машинный код сериализуется в список JSON. Один элемент списка -- одна инструкция.
- Индекс списка соответствует адресу инструкции в машинном коде.

Пример:

```json
[
    {
        "opcode": "jz",
        "arg": 5
    },
]
```

где:

- `opcode` -- строка с кодом операции (тип: `Opcode`);
- `arg` -- аргумент инструкции (если требуется);
"""

import json
from enum import Enum


class Opcode(str, Enum):
    NOP = "nop"
    LIT = "lit"

    LOAD = "load"
    STORE = "store"

    DUP = "dup"
    OVER = "over"

    ADD = "add"
    SUB = "sub"

    AND = "and"
    OR = "or"
    INV = "invert"
    NEG = "neg"
    ISNEG = "is_neg"

    JMP = "jmp"
    JZ = "jz"

    CALL = "call"
    RET = "RET"

    HALT = "halt"

    def __str__(self):
        return str(self.value)


class Instruction:
    def __init__(self, opcode: Opcode, arg: int | None = None):
        self.opcode: Opcode = opcode
        self.arg: int = arg

    def __str__(self):
        return f"({self.opcode} {self.arg})"

    def __repr__(self):
        return self.__str__()


def write_code(filename, code):
    with open(filename, "w", encoding="utf-8") as file:
        buf = []
        for instr in code:
            buf.append(json.dumps(instr))
        file.write("[\n" + ",\n ".join(buf) + "\n]")


def read_code(filename):
    with open(filename, encoding="utf-8") as file:
        file_code = json.loads(file.read())

    program_code = []
    for instr in file_code:
        program_code.append(Instruction(
            Opcode(instr["opcode"]),
            instr["arg"] if "arg" in instr else None
        ))

    return program_code
