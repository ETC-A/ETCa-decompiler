from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from decoder_lib import check, inst, label, DecodedInstruction, DecodedAtom, BitVector, BitSection, \
    ExtensionRequirement, pat, DecodedPart, RenderContext, DecodedJumpTarget

noreq = ExtensionRequirement(())

SIZES = {
    1: ('x', noreq)
}


@dataclass
class BaseRegister(DecodedPart):
    bit_section: BitSection
    index: int
    known_size: DecodedPart = None

    required_extensions = noreq

    def render(self, context: RenderContext) -> str:
        size = self.known_size or context.values.get('size')
        return f"%r{size.render(context) if size else ''}{self.index}"


@dataclass
class BasicInstruction(DecodedInstruction, ABC):
    size: DecodedPart
    arg1: DecodedPart
    arg2: DecodedPart
    opcode_bit_section: BitSection
    general_bit_section: BitSection

    name: ClassVar[str]
    format_string: ClassVar[str] = "{name}{size} {arg1}, {arg2}"
    general_requirement: ClassVar[ExtensionRequirement] = noreq

    has_2_reg_mode: ClassVar[bool] = False
    has_reg_immediate: ClassVar[bool] = False
    sign_extend: ClassVar[bool]
    extra_check = None

    def __init_subclass__(cls, **kwargs):
        if 'opcode' in kwargs:
            BASE_OPCODES[kwargs.pop('opcode')].append(cls)

    def get_rendered_arguments(self, context: RenderContext) -> dict[str, str]:
        context.push("size", self.size)
        res = {
            'name': self.name,
            'size': self.size.render(context),
            'arg1': self.arg1.render(context),
            'arg2': self.arg2.render(context),
        }
        context.pop("size")
        return res

    @property
    def atoms(self):
        return {
            '_general': ('', self.general_bit_section, self.general_requirement),
            'opcode': (self.name, self.opcode_bit_section, noreq),
            'size': self.size,
            'arg1': self.arg1,
            'arg2': self.arg2,
        }


BASE_OPCODES: dict[int, list[type[BasicInstruction]]] = {i: [] for i in range(16)}


class TwoReg(BasicInstruction):
    has_2_reg_mode = True


class RegImm(BasicInstruction):
    has_reg_immediate = True


class SignExtend(BasicInstruction):
    sign_extend = True


class ZeroExtend(BasicInstruction):
    sign_extend = False


# region Base Instruction
class Add(TwoReg, RegImm, SignExtend, opcode=0):    name = "add"


class Sub(TwoReg, RegImm, SignExtend, opcode=1):    name = "sub"


class Rsub(TwoReg, RegImm, SignExtend, opcode=2):    name = "rsub"


class Comp(TwoReg, RegImm, SignExtend, opcode=3):    name = "comp"


class Or(TwoReg, RegImm, SignExtend, opcode=4):    name = "or"


class Xor(TwoReg, RegImm, SignExtend, opcode=5):    name = "xor"


class And(TwoReg, RegImm, SignExtend, opcode=6):    name = "and"


class Test(TwoReg, RegImm, SignExtend, opcode=7):    name = "test"


class Movz(TwoReg, RegImm, ZeroExtend, opcode=8):    name = "movz"


class Movs(TwoReg, RegImm, SignExtend, opcode=9):    name = "movs"


class Load(TwoReg, RegImm, ZeroExtend, opcode=10):    name = "load"


class Store(TwoReg, RegImm, ZeroExtend, opcode=11):    name = "store"


class Slo(RegImm, ZeroExtend, opcode=12):    name = "slo"


class ReadCR(ZeroExtend, opcode=14):    name = "readcr"


class WriteCR(ZeroExtend, opcode=15):    name = "writecr"


# endregion

@pat("reg", "RRR")
def reg(RRR, _other: BitSection):
    yield BaseRegister(RRR.bit_section, int(RRR))


@pat("abm", "{a:reg} {b:reg} 00")
def basic_abm(a, b, _other):
    yield "reg_reg", a, b


@pat("ri", "{a:reg} IIIII")
def basic_abm(a, IIIII, _other):
    yield "reg_imm", a, IIIII


@inst("00 SS CCCC  {args:abm}")
@inst("01 SS CCCC  {args:ri}")
def basic_instruction(SS, CCCC: BitVector, args, _other: BitSection):
    check(SS in SIZES)
    opcodes = BASE_OPCODES[int(CCCC)]
    mode, a, b = args
    assert mode in ("reg_reg", "reg_imm")
    for opcode in opcodes:
        if mode == "reg_reg" and not opcode.has_2_reg_mode:
            continue
        if mode == "reg_imm":
            if not opcode.has_reg_immediate:
                continue
            if opcode.sign_extend:
                b = b.signed()
            else:
                b = b.unsigned()
            b = DecodedAtom(b.bit_section, noreq, "imm", int(b))
        if opcode.extra_check is not None and not opcode.extra_check(a, b):
            continue
        yield opcode(
            size=DecodedAtom(SS.bit_section, SIZES[SS][1], "size", SIZES[SS][0]),
            arg1=a,
            arg2=b,
            opcode_bit_section=CCCC.bit_section,
            general_bit_section=_other,
        )


@dataclass
class Condition(DecodedPart):
    name: ClassVar[str]
    bit_section: BitSection
    required_extensions = noreq

    def render(self, context: RenderContext) -> str:
        return self.name

    def __init_subclass__(cls, **kwargs):
        if 'opcode' in kwargs:
            assert kwargs['opcode'] not in BASE_CONDITIONS
            BASE_CONDITIONS[kwargs.pop('opcode')] = cls


BASE_CONDITIONS: dict[int, type[Condition]] = {}


# region Base Conditions
class Zero(Condition, opcode=0): name = "z"


class NotZero(Condition, opcode=1): name = "nz"


class Negative(Condition, opcode=2): name = "n"


class NotNegative(Condition, opcode=3): name = "nn"


class Carry(Condition, opcode=4): name = "c"


class NoCarry(Condition, opcode=5): name = "nc"


class Overflow(Condition, opcode=6): name = "v"


class NoOverflow(Condition, opcode=7): name = "nv"


class BelowOrEqual(Condition, opcode=8): name = "be"


class AboveOrEqual(Condition, opcode=9): name = "a"


class Lower(Condition, opcode=10): name = "l"


class GreaterOrEqual(Condition, opcode=11): name = "ge"


class LessOrEqual(Condition, opcode=12): name = "le"


class Greater(Condition, opcode=13): name = "g"


class Always(Condition, opcode=14):
    name = "mp"


class Never(Condition, opcode=15):
    name = "never"


# endregion

@dataclass
class CondJump(DecodedInstruction):
    cond: Condition
    target: DecodedPart
    general_bit_section: BitSection

    general_requirement: ExtensionRequirement = noreq
    format_string = "j{cond} {target}"

    def get_rendered_arguments(self, context: RenderContext) -> dict[str, str]:
        return {
            "cond": self.cond.name,
            "target": self.target.render(context)
        }

    @property
    def atoms(self):
        return {
            '_general': ('', self.general_bit_section, self.general_requirement),
            'cond': self.cond,
            'target': self.target
        }


class Hlt(CondJump):
    format_string = "hlt{cond}"

    def get_rendered_arguments(self, context: RenderContext) -> dict[str, str]:
        return {
            "cond": self.cond.name if not isinstance(self.cond, Always) else ""
        }


class Nop(CondJump):
    format_string = "nop {target}"

    def get_rendered_arguments(self, context: RenderContext) -> dict[str, str]:
        match self.target:
            case DecodedJumpTarget(is_relative=True, value=0):
                return {"target": ""}
            case _:
                return {"target": self.target.render(context)}


@pat("cond", "CCCC")
def condition(CCCC, _other):
    assert _other == ()
    yield BASE_CONDITIONS[int(CCCC)](CCCC.bit_section)


@inst("10 0 D {c:cond}  {d:8}")
def conditional_jump(D, c, d, _other):
    dest = (D @ d).signed(9)
    l = label(rel_target=dest)
    if isinstance(c, Never):
        yield Nop(c, l, _other)
    elif dest == 0:
        yield Hlt(c, l, _other)
    else:
        yield CondJump(c, l, _other)
