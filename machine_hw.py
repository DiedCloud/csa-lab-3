import logging
import sys
from enum import Enum

from isa import Opcode, read_data_and_code, Instruction


class Signal(str, Enum):
    # Memory
    WriteMem = "WriteMem"
    ReadMem = "ReadMem"

    # ALU multiplexer latch
    TOSRight = "TOSRight"
    SPRight = "SPRight"
    ZeroRight = "ZeroRight"

    IncLeft = "IncLeft"
    DecLeft = "DecLeft"
    ZeroLeft = "ZeroLeft"
    TOSLeft = "TOSLeft"

    SumALU = "SumALU"
    SubALU = "SubALU"
    AndALU = "AndALU"
    OrALU = "OrALU"
    NegALU = "NegALU"
    InvertRightALU = "InvertRightALU"
    ISNEG = "ISNEG"

    # TOS multiplexer latch
    SaveALU = "SaveALU"
    SaveLIT = "SaveLIT"

    # latch
    LatchSP = "LatchSP"

    #Stack
    WriteFromTOS = "WriteFromTOS"
    TosToTos1 = "TosToTos1"
    ReadToTOS = "ReadToTOS"
    ReadToTOS1 = "ReadToTOS1"

    # Controlling
    PCJumpTypeJNZ = "PCJumpTypeJNZ"
    PCJumpTypeJump = "PCJumpTypeJump"
    PCJumpTypeNext = "PCJumpTypeNext"
    PCJumpTypeRET = "PCJumpTypeRET"
    MicroProgramCounterZero = "MicroProgramCounterZero"
    MicroProgramCounterOpcode = "MicroProgramCounterOpcode"
    MicroProgramCounterNext = "MicroProgramCounterNext"

    # Return Stack
    PushRetStack = "PushRetStack"
    PopRetStack = "PopRetStack"

    # latch
    LatchPC = "LatchPC"
    LatchMPCounter = "LatchMPCounter"


class ALU:
    SIGNAL_TO_OPERATION = {
        Signal.SumALU: lambda a, b: a+b,
        Signal.SubALU: lambda a, b: a-b,
        Signal.AndALU: lambda a, b: a and b,
        Signal.OrALU: lambda a, b: a or b,
        Signal.NegALU: lambda _, b: -b,
        Signal.ISNEG: lambda _, b: -1 if b < 0 else 0,
        Signal.InvertRightALU: lambda _, b: -1 if b == 0 else 0,
    }

    def run(self, signal: Signal, left: int, right: int):
        return self.SIGNAL_TO_OPERATION[signal](left, right)


class DataPath:
    data_memory = None

    tos = None
    tos_1 = None
    stack_pointer = None
    stack = None

    input_buffer = None
    output_buffer = None
    alu = ALU()

    WRITE_MEM_IO_MAPPING = 0
    READ_MEM_IO_MAPPING = 1

    def __init__(self, data_memory, input_buffer: list[str]):
        self.data_memory = data_memory

        self.tos = 0
        self.tos1 = 0
        self.stack_pointer = 1
        self.stack = [0, 0]

        self.input_buffer: list[str] = input_buffer
        self.output_buffer: list[str] = []


    def write_memory(self, data_address: int, value: int): # передать тип вывода?
        self.data_memory[data_address] = value
        if data_address == self.WRITE_MEM_IO_MAPPING:
            self.output_buffer.append(str(value))

    def read_memory(self, data_address: int):
        res = self.data_memory[data_address]
        if data_address == self.READ_MEM_IO_MAPPING:
            if len(self.input_buffer) <= 0:
                raise EOFError
            res = self.input_buffer[0]
            self.input_buffer = self.input_buffer[1::]
        return res

    def latch_tos(self, value: int):
        self.tos = value

    def latch_tos1(self, value: int):
        self.tos1 = value

    def latch_sp(self, value: int):
        self.stack_pointer = value

    def write_from_tos(self):
        while len(self.stack) <= self.stack_pointer:
            self.stack.append(0)
        self.stack[self.stack_pointer] = self.tos

    def is_not_zero(self):
        return self.tos != 0


class HLT(StopIteration):
    pass


class ControlUnit:
    program = None
    program_counter = None
    data_path = None
    return_stack = None
    return_stack_pointer = None
    _tick = None

    def __init__(self, program: list[Instruction], data_path: DataPath):
        self.program: list[Instruction] = program
        self.program_counter: int = 0
        self.data_path: DataPath = data_path
        self.return_stack: list[int] = [0]
        self.return_stack_pointer: int = 0
        self._tick: int = 0

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def decode_and_execute_control_flow_instruction(self, instruction: Instruction):
        if instruction.opcode is Opcode.HALT:
            raise StopIteration()

        if instruction.opcode is Opcode.JNZ:
            self.program_counter = self.program[self.program_counter].arg if self.data_path.is_not_zero() else self.program_counter + 1
            self.tick()

            alu_left = -1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            self.data_path.latch_tos(self.data_path.stack[self.data_path.stack_pointer])
            self.tick()

            alu_left = -1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            self.data_path.latch_tos1(self.data_path.stack[self.data_path.stack_pointer])
            self.tick()

            alu_left = +1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()
            return True


        if instruction.opcode is Opcode.JMP:
            self.program_counter = self.program[self.program_counter].arg
            self.tick()
            return True

        if instruction.opcode is Opcode.CALL:
            self.return_stack_pointer += 1
            # наличие ветвления - особенность модели
            if len(self.return_stack) > self.return_stack_pointer: # если элемент уже был
                self.return_stack[self.return_stack_pointer] = self.program_counter + 1
            else: # если надо увеличить размер стека
                self.return_stack.append(self.program_counter + 1)
            self.tick()

            self.program_counter = self.program[self.program_counter].arg
            self.tick()
            return True

        if instruction.opcode is Opcode.RET:
            self.program_counter = self.return_stack[self.return_stack_pointer]
            self.tick()

            self.return_stack_pointer -= 1
            self.tick()
            return True

        return False

    def alu_two_arg_instruction(self, instruction):
        """
        Объединяет alu-specific инструкции с двумя аргументами.
         Не соответствует варианту с микрокодом, ведь в нем нет поддержки прыжков по микро-инструкциям.
        """
        alu_left = self.data_path.tos1
        alu_right = self.data_path.tos

        signal = {
            Opcode.ADD: Signal.SumALU,
            Opcode.SUB: Signal.SubALU,
            Opcode.AND: Signal.AndALU,
            Opcode.OR: Signal.OrALU,
        }
        alu_res = self.data_path.alu.run(signal[instruction.opcode], alu_left, alu_right)

        self.data_path.latch_sp(alu_res)
        self.tick()

        alu_left = -1
        alu_right = self.data_path.stack_pointer
        alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
        self.data_path.latch_sp(alu_res)
        self.tick()

        self.data_path.write_from_tos()
        self.tick()

        alu_left = -1
        alu_right = self.data_path.stack_pointer
        alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
        self.data_path.latch_sp(alu_res)
        self.tick()

        self.data_path.latch_tos1(self.data_path.stack[self.data_path.stack_pointer])
        self.tick()

        alu_left = +1
        alu_right = self.data_path.stack_pointer
        alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
        self.data_path.latch_sp(alu_res)
        self.tick()

    def alu_one_arg_instruction(self, instruction: Instruction):
        """
        Объединяет alu-specific инструкции с одним аргументом.
         Не соответствует варианту с микрокодом, ведь в нем нет поддержки прыжков по микро-инструкциям.
        """
        alu_left = 0
        alu_right = self.data_path.tos

        signal = {
            Opcode.INV: Signal.InvertRightALU,
            Opcode.NEG: Signal.NegALU,
            Opcode.ISNEG: Signal.ISNEG,
        }
        alu_res = self.data_path.alu.run(signal[instruction.opcode], alu_left, alu_right)

        self.data_path.latch_tos(alu_res)
        self.tick()

        self.data_path.write_from_tos()
        self.tick()

    def decode_and_execute_instruction(self, instruction: Instruction):
        if self.decode_and_execute_control_flow_instruction(instruction):
            return

        if instruction.opcode == Opcode.NOP:
            pass
        if instruction.opcode == Opcode.LIT:
            self.data_path.latch_tos(self.program[self.program_counter].arg)
            self.tick()

            self.data_path.latch_tos1(self.data_path.stack[self.data_path.stack_pointer])
            self.tick()

            alu_left = 1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            self.data_path.write_from_tos()
            self.tick()

        if instruction.opcode == Opcode.LOAD:
            self.data_path.latch_tos(self.data_path.read_memory(self.data_path.tos))
            self.tick()
            self.data_path.write_from_tos()
            self.tick()
        if instruction.opcode == Opcode.STORE:
            self.data_path.write_memory(self.data_path.tos, self.data_path.tos1)
            self.tick()

            alu_left = -1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            alu_left = -1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            self.data_path.latch_tos(self.data_path.stack[self.data_path.stack_pointer])
            self.tick()

            alu_left = -1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            self.data_path.latch_tos1(self.data_path.stack[self.data_path.stack_pointer])
            self.tick()

            alu_left = +1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

        if instruction.opcode == Opcode.DUP:
            alu_left = +1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            self.data_path.write_from_tos()
            self.tick()

            self.data_path.latch_tos1(self.data_path.stack[self.data_path.stack_pointer])
            self.tick()
        if instruction.opcode == Opcode.OVER:
            alu_left = self.data_path.tos1
            alu_right = 0
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            self.data_path.latch_tos1(self.data_path.stack[self.data_path.stack_pointer])
            self.tick()

            alu_left = +1
            alu_right = self.data_path.stack_pointer
            alu_res = self.data_path.alu.run(Signal.SumALU, alu_left, alu_right)
            self.data_path.latch_sp(alu_res)
            self.tick()

            self.data_path.write_from_tos()
            self.tick()

        if instruction.opcode in (Opcode.ADD, Opcode.SUB, Opcode.AND, Opcode.OR):
            self.alu_two_arg_instruction(instruction)

        if instruction.opcode in (Opcode.INV, Opcode.NEG, Opcode.ISNEG):
            self.alu_one_arg_instruction(instruction)

        self.program_counter += 1

    def run(self, limit):
        instr_counter = 0

        logging.debug("%s", self)
        try:
            while True:
                self.decode_and_execute_instruction(self.program[self.program_counter])
                logging.debug("%s", self.__repr__())

                if instr_counter >= limit:
                    logging.warning("Limit exceeded!")
                    break
        except EOFError:
            logging.warning("Input buffer is empty!")
        except HLT:
            logging.info("Program has ended with halt")

        logging.info("output_buffer: %s", repr("".join(self.data_path.output_buffer)))
        return "".join(self.data_path.output_buffer), instr_counter, self.current_tick()

    def __repr__(self):
        state_repr = (
            f"TICK: {self._tick:3}\t"
            f"PC: {self.program_counter:3}\t"
            f"TOS: {self.data_path.tos}\t"
            f"TOS1: {self.data_path.tos1}\t"
            f"SP: {self.data_path.stack_pointer}\t"
        )

        instr = self.program[self.program_counter]
        opcode = instr.opcode
        instr_repr = str(opcode)

        if instr.arg is not None:
            instr_repr += f" {instr.arg}"

        return f"{state_repr}\n{instr_repr}"


def main(code_file, input_file):
    data, code = read_data_and_code(code_file)
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    data_path = DataPath(data, input_token)
    control_unit = ControlUnit(code, data_path)
    output, instr_counter, ticks = control_unit.run(1000)

    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine_hw.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
