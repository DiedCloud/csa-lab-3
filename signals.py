from enum import Enum


class Signal(str, Enum):
    # Memory
    WriteMem = "WriteMem"

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
    ReadMem = "ReadMem"
    ReadToTOS = "ReadToTOS"

    LatchTOS1 = "ReadToTOS1"

    # latch
    LatchSP = "LatchSP"

    # Stack
    WriteFromTOS = "WriteFromTOS"

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
