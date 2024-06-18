from signals import Signal


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
    tos1 = None
    stack_pointer = None
    stack = None

    input_buffer = None
    output_buffer = None
    alu = ALU()

    WRITE_MEM_IO_MAPPING_INT = 0 # Устройство, выводящее значение ячеек
    WRITE_MEM_IO_MAPPING_CHAR = 1 # Устройство, выводящее символы
    READ_MEM_IO_MAPPING = 2

    def __init__(self, data_memory, input_buffer: list[str]):
        self.data_memory = data_memory

        self.tos = 0
        self.tos1 = 0
        self.stack_pointer = 1
        self.stack = [0, 0]

        self.input_buffer: list[str] = input_buffer
        self.output_buffer: list[str] = []


    def write_memory(self, data_address: int, value: int):
        self.data_memory[data_address] = value
        if data_address == self.WRITE_MEM_IO_MAPPING_CHAR:
            self.output_buffer.append(chr(value))
        if data_address == self.WRITE_MEM_IO_MAPPING_INT:
            self.output_buffer.append(str(value))

    def read_memory(self, data_address: int):
        if data_address == self.READ_MEM_IO_MAPPING:
            if len(self.input_buffer) <= 0:
                res = 0 # EOF
            else:
                res = ord(self.input_buffer[0])
                self.input_buffer = self.input_buffer[1::]
        else:
            res = self.data_memory[data_address]
        assert isinstance(res, int), "Memory can contain only integers"
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
