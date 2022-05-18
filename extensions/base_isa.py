from collections.abc import Callable
from dataclasses import dataclass

from decoder_lib import check, pat, label, DecodedInstruction


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
    10: [BaseIsaOpcodeInfo('load')],
    11: [BaseIsaOpcodeInfo('store')],
    12: [BaseIsaOpcodeInfo('slo', has_2_reg_mode=False, sign_extend=False)],
    13: [],
    14: [BaseIsaOpcodeInfo('readcr', has_2_reg_mode=False, sign_extend=False)],
    15: [BaseIsaOpcodeInfo('writecr', has_2_reg_mode=False, sign_extend=False)]
}


@pat("00 SS CCCC  AAA BBB 00")
def reg_reg(SS, CCCC, AAA, BBB):
    check(SS in SIZES)
    opcodes = BASE_OPCODES[CCCC]
    for opcode in opcodes:
        if not opcode.has_2_reg_mode:
            continue
        if opcode.extra_check is not None and not opcode.extra_check(AAA, BBB):
            continue
        args = dict(name=opcode.name,
                    size=SIZES[SS][0],
                    arg1=f"%r{SIZES[SS][0]}{AAA.dec(1)}",
                    arg2=f"%r{SIZES[SS][0]}{BBB.dec(1)}")
        yield DecodedInstruction(opcode.format_string.format(**args),
                                 (*SIZES[SS][1], *opcode.required_extensions))


@pat("01 SS CCCC  AAA IIIII")
def reg_immediate(SS, CCCC, AAA, IIIII):
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
        args = dict(name=opcode.name,
                    size=SIZES[SS][0],
                    arg1=f"%r{SIZES[SS][0]}{AAA.dec(1)}",
                    arg2=imm.dec())
        yield DecodedInstruction(opcode.format_string.format(**args),
                                 (*SIZES[SS][1], *opcode.required_extensions))


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


@pat("10 0 D CCCC  {d:8}")
def condition(D, CCCC, d):
    dest = (D @ d).signed(9)
    if CCCC == 14 and dest == 0:
        yield DecodedInstruction(f"hlt", ())
    elif CCCC == 15:
        if dest == 0:
            yield DecodedInstruction(f"nop", ())
        else:
            yield DecodedInstruction(f"nop {label(rel_target=dest)}", ())
    else:
        cond_name = BASE_CONDITIONS[CCCC]
        yield DecodedInstruction(f"j{cond_name} {label(rel_target=dest)}", ())
