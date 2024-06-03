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


class HLT(KeyError):
    pass


class ControlUnit:
    program = None
    program_counter = None
    data_path = None
    return_stack = None
    return_stack_pointer = None
    _tick = None
    microprogram = (
        (Signal.MicroProgramCounterOpcode, Signal.LatchMPCounter),  # 0 - Instruction fetch

        # NOP
        (Signal.PCJumpTypeNext, Signal.LatchPC, Signal.MicroProgramCounterZero, Signal.LatchMPCounter),  # 1

        # LIT
        (Signal.SaveLIT,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 2
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 3
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 4
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 5

        # LOAD
        (Signal.ReadMem,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 6
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 7

        # STORE
        (Signal.WriteMem,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 8
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 9
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 10
        (Signal.ReadToTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 11
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 12
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 13
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 14

        # DUP
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 15
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 16
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 17

        # OVER
        (Signal.TOSLeft, Signal.ZeroRight,
         Signal.SumALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 18
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 19
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 20
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 21

        # ADD
        (Signal.TOSLeft, Signal.TOSRight,
         Signal.SumALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 22
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 23
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 24
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 25
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 26
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 27

        # SUB
        (Signal.TOSLeft, Signal.TOSRight,
         Signal.SubALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 28
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 29
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 30
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 31
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 32
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 33

        # AND
        (Signal.TOSLeft, Signal.TOSRight,
         Signal.AndALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 34
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 35
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 36
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 37
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 38
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 39

        # OR
        (Signal.TOSLeft, Signal.TOSRight,
         Signal.OrALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 40
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 41
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 42
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 43
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 44
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 45

        # INV
        (Signal.ZeroLeft, Signal.TOSRight,
         Signal.InvertRightALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 46
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 47

        # NEG
        (Signal.ZeroLeft, Signal.TOSRight,
         Signal.NegALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 48
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 49

        # ISNEG
        (Signal.ZeroLeft, Signal.TOSRight,
         Signal.ISNEG, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 50
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 51

        # JMP
        (Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeJump, Signal.LatchPC),  # 52

        # JNZ
        (Signal.MicroProgramCounterNext, Signal.LatchMPCounter,
         Signal.PCJumpTypeJNZ, Signal.LatchPC),  # 53
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 54
        (Signal.ReadToTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 55
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 56
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 57
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter),  # 58

        # CALL
        (Signal.PushRetStack,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 59
        (Signal.MicroProgramCounterZero, Signal.LatchMPCounter, Signal.PCJumpTypeJump, Signal.LatchPC),  # 60

        # RET
        (Signal.MicroProgramCounterNext, Signal.LatchMPCounter,
         Signal.PCJumpTypeRET, Signal.LatchPC),  # 61
        (Signal.PopRetStack,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter),  # 62
    )
    microprogram_counter = None

    @staticmethod
    def opcode_to_mc(opcode: Opcode):
        try:
            return {
                Opcode.NOP: 1,
                Opcode.LIT: 2,
                Opcode.LOAD: 6,
                Opcode.STORE: 8,
                Opcode.DUP: 15,
                Opcode.OVER: 18,
                Opcode.ADD: 22,
                Opcode.SUB: 28,
                Opcode.AND: 34,
                Opcode.OR: 40,
                Opcode.INV: 46,
                Opcode.NEG: 48,
                Opcode.ISNEG: 50,
                Opcode.JMP: 52,
                Opcode.JNZ: 53,
                Opcode.CALL: 59,
                Opcode.RET: 61,
            }[opcode]
        except KeyError:
            raise HLT()

    def __init__(self, program: list[Instruction], data_path: DataPath):
        self.program: list[Instruction] = program
        self.program_counter: int = 0
        self.data_path: DataPath = data_path
        self.return_stack: list[int] = [0]
        self.return_stack_pointer: int = 0
        self._tick: int = 0
        self.microprogram_counter: int = 0
        self.prev_mpc: int = 0

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def on_signal_latch_program_counter(self, microcode: tuple):
        if Signal.PCJumpTypeNext in microcode:
            self.program_counter += 1
        elif Signal.PCJumpTypeJNZ in microcode:
            self.program_counter = self.program[self.program_counter].arg if self.data_path.is_not_zero() else self.program_counter + 1
        elif Signal.PCJumpTypeJump in microcode:
            self.program_counter = self.program[self.program_counter].arg
        elif Signal.PCJumpTypeRET in microcode:
            self.program_counter = self.return_stack[self.return_stack_pointer]

    def on_signal_latch_microprogram_counter(self, microcode: tuple):
        if Signal.MicroProgramCounterNext in microcode:
            self.microprogram_counter += 1
        elif Signal.MicroProgramCounterOpcode in microcode:
            self.microprogram_counter = self.opcode_to_mc(self.program[self.program_counter].opcode)
        elif Signal.MicroProgramCounterZero in microcode:
            self.microprogram_counter = 0

    def decode_and_execute_signals(self, microcode: tuple):
        alu_res = 0
        for signal in microcode:
            match signal:
                case Signal.WriteMem:
                    self.data_path.write_memory(self.data_path.tos, self.data_path.tos1)
                case Signal.ReadMem:
                    self.data_path.latch_tos(self.data_path.read_memory(self.data_path.tos))
                case (
                    Signal.SumALU |
                    Signal.SubALU |
                    Signal.AndALU |
                    Signal.OrALU |
                    Signal.InvertRightALU |
                    Signal.ISNEG |
                    Signal.NegALU
                ):
                    if Signal.TOSLeft in microcode:
                        alu_left = self.data_path.tos1
                    elif Signal.IncLeft in microcode:
                        alu_left = 1
                    elif Signal.DecLeft in microcode:
                        alu_left = -1
                    elif Signal.ZeroLeft in microcode:
                        alu_left = 0
                    else:
                        raise ValueError("Nothing chosen on left alu input")

                    if Signal.TOSRight in microcode:
                        alu_right = self.data_path.tos
                    elif Signal.SPRight in microcode:
                        alu_right = self.data_path.stack_pointer
                    elif Signal.ZeroRight in microcode:
                        alu_right = 0
                    else:
                        raise ValueError("Nothing chosen on right alu input")

                    alu_res = self.data_path.alu.run(signal, alu_left, alu_right)
                    if Signal.SaveALU in microcode:
                        self.data_path.latch_tos(alu_res)

                case Signal.SaveLIT:
                    self.data_path.latch_tos(self.program[self.program_counter].arg)
                case Signal.LatchSP:
                    self.data_path.latch_sp(alu_res)
                case Signal.WriteFromTOS:
                    self.data_path.write_from_tos()
                case Signal.TosToTos1:
                    self.data_path.latch_tos1(self.data_path.tos)
                case Signal.ReadToTOS:
                    self.data_path.latch_tos(self.data_path.stack[self.data_path.stack_pointer])
                case Signal.ReadToTOS1:
                    self.data_path.latch_tos1(self.data_path.stack[self.data_path.stack_pointer])

                case Signal.PushRetStack:
                    self.return_stack_pointer += 1
                    if len(self.return_stack) > self.return_stack_pointer:
                        self.return_stack[self.return_stack_pointer] = self.program_counter + 1
                    else:
                        self.return_stack.append(self.program_counter + 1)
                case Signal.PopRetStack:
                    self.return_stack_pointer -= 1

                case Signal.LatchPC:
                    self.on_signal_latch_program_counter(microcode)
                case Signal.LatchMPCounter:
                    self.on_signal_latch_microprogram_counter(microcode)
                case _:
                    pass


    def run(self, limit):
        instr_counter = 0

        logging.debug("%s", self)
        try:
            while True:
                if self.microprogram_counter == 0:
                    instr_counter += 1
                    logging.debug(f"Instruction #{instr_counter}")

                self.prev_mpc = self.microprogram_counter
                self.decode_and_execute_signals(self.microprogram[self.microprogram_counter])
                self.tick()
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
            f"PREV_MPC: {self.prev_mpc}\t"
            f"CUR_MPC: {self.microprogram_counter}\t"
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
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
