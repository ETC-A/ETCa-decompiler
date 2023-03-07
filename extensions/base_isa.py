from collections.abc import Callable
from dataclasses import dataclass

from decoder_lib import check, inst, label, DecodedInstruction, DecodedAtom, BitVector, BitSection


@dataclass(frozen=True)
class BaseIsaOpcodeInfo:
    name: str
    format_string: str = "{name}{size} {arg1}, {arg2}"
    has_2_reg_mode: bool = True
    has_reg_immediate: bool = True
    sign_extend: bool = True
    extra_check: Callable = None
    required_extensions: tuple[str, ...] = ()


SIZES = {
    1: ('x', ())
}

BASE_OPCODES = {
    0: [BaseIsaOpcodeInfo('add')],
    1: [BaseIsaOpcodeInfo('sub')],
    2: [BaseIsaOpcodeInfo('rsub')],
    3: [BaseIsaOpcodeInfo('cmp')],
    4: [BaseIsaOpcodeInfo('or')],
    5: [BaseIsaOpcodeInfo('xor')],
    6: [BaseIsaOpcodeInfo('and')],
    7: [BaseIsaOpcodeInfo('test')],
    8: [BaseIsaOpcodeInfo('movz', sign_extend=False)],
    9: [BaseIsaOpcodeInfo('movs')],
    10: [BaseIsaOpcodeInfo('load', sign_extend=False)],
    11: [BaseIsaOpcodeInfo('store', sign_extend=False)],
    12: [BaseIsaOpcodeInfo('slo', has_2_reg_mode=False, sign_extend=False)],
    13: [],
    14: [BaseIsaOpcodeInfo('readcr', has_2_reg_mode=False, sign_extend=False)],
    15: [BaseIsaOpcodeInfo('writecr', has_2_reg_mode=False, sign_extend=False)]
}


@inst("00 SS CCCC  AAA BBB 00")
def reg_reg(SS, CCCC: BitVector, AAA, BBB, _other: BitSection):
    check(SS in SIZES)
    opcodes = BASE_OPCODES[CCCC]
    for opcode in opcodes:
        if not opcode.has_2_reg_mode:
            continue
        if opcode.extra_check is not None and not opcode.extra_check(AAA, BBB):
            continue
        yield DecodedInstruction("{opcode}{size} %r{size}{a}, %r{size}{b}", {
            "opcode": DecodedAtom(CCCC.bit_section, "opcode", opcode.name),
            "size": DecodedAtom(SS.bit_section, "size", SIZES[SS][0]),
            "a": DecodedAtom(AAA.bit_section, "register", AAA.dec(1)),
            "b": DecodedAtom(BBB.bit_section, "register", BBB.dec(1)),
        }, general_bit_section=_other)


@inst("01 SS CCCC  AAA IIIII")
def reg_immediate(SS, CCCC, AAA, IIIII, _other):
    check(SS in SIZES)
    opcodes = BASE_OPCODES[CCCC]
    for opcode in opcodes:
        if not opcode.has_reg_immediate:
            continue
        if opcode.sign_extend:
            imm = IIIII.signed(5)
        else:
            imm = IIIII.unsigned(5)
        if opcode.extra_check is not None and not opcode.extra_check(AAA, IIIII):
            continue
        yield DecodedInstruction("{opcode}{size} %r{size}{a}, {imm}", {
            "opcode": DecodedAtom(CCCC.bit_section, "opcode", opcode.name),
            "size": DecodedAtom(SS.bit_section, "size", SIZES[SS][0]),
            "a": DecodedAtom(AAA.bit_section, "register", AAA.dec(1)),
            "imm": DecodedAtom(imm.bit_section, "register", imm.dec(1)),
        }, general_bit_section=_other)


BASE_CONDITIONS = {
    0: 'z',
    1: 'nz',
    2: 'n',
    3: 'nn',
    4: 'c',
    5: 'nc',
    6: 'v',
    7: 'nv',
    8: 'be',
    9: 'a',
    10: 'l',
    11: 'ge',
    12: 'le',
    13: 'g',
    14: 'mp',
}


@inst("10 0 D CCCC  {d:8}")
def condition(D, CCCC, d, _other):
    dest = (D @ d).signed(9)
    if CCCC == 14 and dest == 0:
        yield DecodedInstruction("{opcode}", {
            "opcode": DecodedAtom((dest @ CCCC).bit_section, "special_opcode", "hlt")
        }, general_bit_section=_other)
    elif CCCC == 15:
        if dest == 0:
            yield DecodedInstruction("{opcode}", {
                "opcode": DecodedAtom((dest @ CCCC).bit_section, "special_opcode", "nop")
            }, general_bit_section=_other)
        else:
            yield DecodedInstruction("{opcode} {target}", {
                "opcode": DecodedAtom(CCCC.bit_section, "opcode", "nop"),
                "target": label(dest.bit_section, rel_target=dest)
            }, general_bit_section=_other)
    else:
        cond_name = BASE_CONDITIONS[CCCC]
        yield DecodedInstruction("{opcode} {target}", {
            "opcode": DecodedAtom(CCCC.bit_section, "jump_opcode", f"j{cond_name}"),
            "target": label(dest.bit_section, rel_target=dest)
        }, general_bit_section=_other)
