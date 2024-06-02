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


def write_data_and_code(filename, data: list[int | str], code: list[Instruction]):
    with open(filename, "w", encoding="utf-8") as file:
        file.write("{\n\t\"data\":")
        for d in range(len(data)):
            data[d] = data[d] if isinstance(data[d], int) else "\"" + str(data[d]) + "\""
        file.write(" [\n\t\t" + ",\n\t\t".join(data) + "\n\t]")

        file.write(",\n\t\"code\":")
        buf = []
        for instr in code:
            a = instr.arg if isinstance(instr.arg, int) else "\"" + str(instr.arg) + "\""
            buf.append(
                "\t\t{" +
                f"\"opcode\": \"{instr.opcode}\","
                f" \"arg\": {a}" +
                "}")
        file.write(" [\n" + ",\n ".join(buf) + "\n\t]")

        file.write("\n}")

def read_data_and_code(filename):
    with open(filename, encoding="utf-8") as file:
        file = json.loads(file.read())

    data = []
    for d in file["data"]:
        data.append(d)

    program_code = []
    for instr in file["code"]:
        program_code.append(Instruction(
            Opcode(instr["opcode"]),
            instr["arg"] if "arg" in instr else None
        ))

    return data, program_code
