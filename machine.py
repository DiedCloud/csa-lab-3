import logging
import sys
from enum import Enum

from isa import Opcode, read_code


class Signal(None, Enum):
    # Memory
    WriteMem = None
    ReadMem = None

    # ALU multiplexer latch
    TOSRight = None
    SPRight = None
    ZeroRight = None

    IncLeft = None
    DecLeft = None
    ZeroLeft = None
    TOSLeft = None

    SumALU = None
    SubALU = None
    AndALU = None
    OrALU = None
    InvertRightALU = None
    ISNEG = None

    # TOS multiplexer latch
    SaveALU = None
    SaveLIT = None
    SaveMEM = None

    # latch
    LatchTOS = None
    LatchTOS1 = None
    LatchSP = None

    #Stack
    WriteFromTOS = None
    ReadToTOS = None
    ReadToTOS1 = None

    # Controlling
    PCJumpTypeJZ = None
    PCJumpTypeJump = None
    PCJumpTypeNext = None
    PCJumpTypeRET = None
    MicroProgramCounterZero = None
    MicroProgramCounterOpcode = None
    MicroProgramCounterNext = None

    # Return Stack
    PushRetStack = None
    PopRetStack = None

    # latch
    LatchPC = None
    LatchMPCounter = None


class ALU:
    negative: bool = False
    zero: bool = False
    def sum(self, left: int, right: int):
        ans = left + right
        self.negative = ans < 0
        self.zero = ans == 0
        return ans


class DataPath:
    data_memory_size = None
    data_memory = None
    tos = None
    tos_1 = None
    input_buffer = None
    output_buffer = None

    def __init__(self, data_memory_size, input_buffer):
        assert data_memory_size > 0, "Data_memory size should be non-zero"
        self.data_memory_size = data_memory_size
        self.data_memory = [0] * data_memory_size
        self.tos = 0
        self.tos1 = 0
        self.input_buffer = input_buffer
        self.output_buffer = []

    def signal_latch_tos(self, value: int):
        self.tos = value

    def signal_latch_tos1(self, value: int):
        self.tos1 = value

    def zero(self):
        return self.tos == 0


class ControlUnit:
    program = None
    program_counter = None
    data_path = None
    _tick = None
    microprogram = (
        (Signal.MicroProgramCounterOpcode, Signal.LatchMPCounter),  # 0 - Instruction fetch

        # NOP
        (Signal.PCJumpTypeNext, Signal.LatchPC, Signal.MicroProgramCounterZero, Signal.LatchMPCounter),  # 1

        # LIT
        (Signal.SaveLIT,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 2
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 3
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 4

        # LOAD
        (Signal.ReadMem, Signal.SaveMEM,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 5
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 6
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 7
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 8
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 9
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 10

        # STORE
        (Signal.WriteMem, Signal.SaveMEM,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 11
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 12
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 13
        (Signal.ReadToTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 14
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 15
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 16
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 17

        # DUP
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 18
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 19
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 20

        # OVER
        (Signal.TOSLeft, Signal.ZeroRight, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 21
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 22
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 23
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter),  # 24

        # ADD
        (Signal.TOSLeft, Signal.TOSRight,
         Signal.SumALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 25
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 26
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 27
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 28
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 29
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 30

        # SUB
        (Signal.TOSLeft, Signal.TOSRight,
         Signal.SubALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 31
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 32
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 33
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 34
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 35
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 36

        # AND
        (Signal.TOSLeft, Signal.TOSRight,
         Signal.AndALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 38
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 39
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 40
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 41
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 42
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 43

        # OR
        (Signal.TOSLeft, Signal.TOSRight,
         Signal.OrALU, Signal.SaveALU,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 44
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 45
        (Signal.WriteFromTOS,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 46
        (Signal.DecLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 47
        (Signal.ReadToTOS1,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 48
        (Signal.IncLeft, Signal.SPRight,
         Signal.SumALU, Signal.LatchSP,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 49

        # INV
        (Signal.ZeroLeft, Signal.TOSRight,
         Signal.InvertRightALU, Signal.SaveALU,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 50

        # ISNEG
        (Signal.ZeroLeft, Signal.TOSRight,
         Signal.ISNEG, Signal.SaveALU,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 51

        # JMP
        (Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeJump, Signal.LatchPC),  # 52

        # JZ
        (Signal.MicroProgramCounterNext, Signal.LatchMPCounter,
         Signal.PCJumpTypeJZ, Signal.LatchPC),  # 53
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
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter,
         Signal.PCJumpTypeNext, Signal.LatchPC),  # 58

        # CALL
        (Signal.PushRetStack,
         Signal.MicroProgramCounterNext, Signal.LatchMPCounter),  # 59
        (Signal.MicroProgramCounterZero, Signal.LatchMPCounter, Signal.PCJumpTypeNext, Signal.LatchPC),  # 60

        # RET
        (Signal.MicroProgramCounterNext, Signal.LatchMPCounter,
         Signal.PCJumpTypeRET, Signal.LatchPC),  # 61
        (Signal.PopRetStack,
         Signal.MicroProgramCounterZero, Signal.LatchMPCounter),  # 62
    )
    microprogram_counter = None

    @staticmethod
    def opcode_to_mc(opcode: Opcode):
        return {
            Opcode.NOP: 1,
            Opcode.LIT: 2,
            Opcode.LOAD: 5,
            Opcode.STORE: 11,
            Opcode.DUP: 18,
            Opcode.OVER: 21,
            Opcode.ADD: 25,
            Opcode.SUB: 31,
            Opcode.AND: 38,
            Opcode.OR: 44,
            Opcode.INV: 50,
            Opcode.ISNEG: 51,
            Opcode.JMP: 52,
            Opcode.JZ: 53,
            Opcode.CALL: 59,
            Opcode.RET: 61,
        }.get(opcode)

    def __init__(self, program, data_path):
        self.program = program
        self.program_counter = 0
        self.data_path = data_path
        self._tick = 0
        self.microprogram_counter = 0

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def on_signal_latch_program_counter(self, sel_next):
        if sel_next:
            self.program_counter += 1
        else:
            instr = self.program[self.program_counter]
            assert "arg" in instr, "internal error"
            self.program_counter = instr["arg"]

    def on_signal_latch_microprogram_counter(self, microcode: tuple):
        pass

    def decode_and_execute_signals(self, microcode: tuple):
        pass

    def run(self, limit):
        instr_counter = 0

        logging.debug("%s", self)
        try:
            while True:
                if self.microprogram_counter == 0:
                    instr_counter += 1
                    pass # TODO Новая инструкция. В лог.

                self.decode_and_execute_signals(self.microprogram[self.microprogram_counter])
                self.tick()
                logging.debug("%s", self) #?

                if instr_counter >= limit:
                    logging.warning("Limit exceeded!")
                    break
        except EOFError:
            logging.warning("Input buffer is empty!")
        except StopIteration:
            pass

        logging.info("output_buffer: %s", repr("".join(self.data_path.output_buffer)))
        return "".join(self.data_path.output_buffer), instr_counter, self.current_tick()

    def __repr__(self):
        state_repr = "TICK: {:3} PC: {:3} ADDR: {:3} MEM_OUT: {} ACC: {}".format(
            self._tick,
            self.program_counter,
            self.data_path.data_address,
            self.data_path.data_memory[self.data_path.data_address],
            self.data_path.acc,
        )

        instr = self.program[self.program_counter]
        opcode = instr["opcode"]
        instr_repr = str(opcode)

        if "arg" in instr:
            instr_repr += " {}".format(instr["arg"])

        if "term" in instr:
            term = instr["term"]
            instr_repr += "  ('{}'@{}:{})".format(term.symbol, term.line, term.pos)

        return "{} \t{}".format(state_repr, instr_repr)


def main(code_file, input_file):
    code = read_code(code_file)
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    data_path = DataPath(100, input_token)
    control_unit = ControlUnit(code, data_path)
    output, instr_counter, ticks = control_unit.run(1000)

    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
