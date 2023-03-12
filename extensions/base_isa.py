from collections.abc import Callable
from dataclasses import dataclass

from decoder_lib import check, inst, label, DecodedInstruction, DecodedAtom, BitVector, BitSection, \
    ExtensionRequirement, pat

noreq = ExtensionRequirement(())


@dataclass(frozen=True)
class BaseIsaOpcodeInfo:
    name: str
    format_string: str = "{name}{size} {arg1}, {arg2}"
    has_2_reg_mode: bool = True
    has_reg_immediate: bool = True
    sign_extend: bool = True
    extra_check: Callable = None
    required_extensions: ExtensionRequirement = noreq


SIZES = {
    1: ('x', noreq)
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


@pat("reg", "RRR")
def reg(RRR, _other: BitSection):
    yield DecodedAtom(RRR.bit_section, noreq, "register", RRR.dec(1))


@inst("00 SS CCCC  {a:reg} {b:reg} 00")
def reg_reg(SS, CCCC: BitVector, a, b, _other: BitSection):
    check(SS in SIZES)
    opcodes = BASE_OPCODES[CCCC]
    for opcode in opcodes:
        if not opcode.has_2_reg_mode:
            continue
        if opcode.extra_check is not None and not opcode.extra_check(a, b):
            continue
        yield DecodedInstruction("{opcode}{size} %r{size}{a}, %r{size}{b}", {
            "opcode": DecodedAtom(CCCC.bit_section, opcode.required_extensions, "opcode", opcode.name),
            "size": DecodedAtom(SS.bit_section, SIZES[SS][1], "size", SIZES[SS][0]),
            "a": a,
            "b": b,
        }, general_bit_section=_other, general_required_extensions=noreq)


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
            "opcode": DecodedAtom(CCCC.bit_section, opcode.required_extensions, "opcode", opcode.name),
            "size": DecodedAtom(SS.bit_section, SIZES[SS][1], "size", SIZES[SS][0]),
            "a": DecodedAtom(AAA.bit_section, noreq, "register", AAA.dec(1)),
            "imm": DecodedAtom(imm.bit_section, noreq, "register", imm.dec(1)),
        }, general_bit_section=_other, general_required_extensions=noreq)


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
            "opcode": DecodedAtom((dest @ CCCC).bit_section, noreq, "special_opcode", "hlt")
        }, general_bit_section=_other, general_required_extensions=noreq)
    elif CCCC == 15:
        if dest == 0:
            yield DecodedInstruction("{opcode}", {
                "opcode": DecodedAtom((dest @ CCCC).bit_section, noreq, "special_opcode", "nop")
            }, general_bit_section=_other, general_required_extensions=noreq)
        else:
            yield DecodedInstruction("{opcode} {target}", {
                "opcode": DecodedAtom(CCCC.bit_section, noreq, "opcode", "nop"),
                "target": label(rel_target=dest)
            }, general_bit_section=_other, general_required_extensions=noreq)
    else:
        cond_name = BASE_CONDITIONS[CCCC]
        yield DecodedInstruction("{opcode} {target}", {
            "opcode": DecodedAtom(CCCC.bit_section, noreq, "jump_opcode", f"j{cond_name}"),
            "target": label(rel_target=dest)
        }, general_bit_section=_other, general_required_extensions=noreq)
