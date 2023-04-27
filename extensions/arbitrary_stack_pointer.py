from decoder_lib import Extension, ExtensionRequirement
from extensions.base_isa import TwoReg, ZeroExtend, RegImm
from extensions.stack_and_functions import saf

asp = Extension("arbitrary-stack-pointer", "asp", (1, 7))
asp_req = ExtensionRequirement.single(asp, saf)


class Pop(TwoReg, ZeroExtend, opcode=12):
    name = "pop"
    format_string = "{opcode}{size}-using {arg1}, {arg2}"
    required_extensions = asp_req

    @classmethod
    def extra_check(cls, a, b):
        return b.index != 6


class Push(TwoReg, RegImm, ZeroExtend, opcode=13):
    name = "push"
    format_string = "{name}{size}-using {arg1}, {arg2}"
    required_extensions = asp_req

    @classmethod
    def extra_check(cls, a, b):
        return a.index != 6
