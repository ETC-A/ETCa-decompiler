from collections import defaultdict

from decoder_lib import pat, DecodedInstruction, label, check, BitSection, DecodedAtom, inst, BitVector, Extension, \
    ExtensionRequirement
from .base_isa import BasicInstruction, SIZES, noreq, TwoReg, RegImm, SignExtend, CondJump, Always, Hlt
from .stack_and_functions import Call, saf

EXPANDED_OPCODES = defaultdict(list)

eoc = Extension("expanded-opcodes", "eoc", (2, 0))
eoc_req = ExtensionRequirement.single(eoc)


class ExpandedOpcode(BasicInstruction):
    general_requirement = eoc_req

    def __init_subclass__(cls, **kwargs):
        if 'expanded_opcode' in kwargs:
            EXPANDED_OPCODES[kwargs.pop('expanded_opcode')].append(cls)


class ADC(ExpandedOpcode, TwoReg, RegImm, SignExtend, expanded_opcode=0):
    name = "adc"


class SBB(ExpandedOpcode, TwoReg, RegImm, SignExtend, expanded_opcode=1):
    name = "sbb"


class RSBB(ExpandedOpcode, TwoReg, RegImm, SignExtend, expanded_opcode=2):
    name = "rsbb"


@inst("111 0 {C5:5} 0 SS {C4:4}  {args:abm}")
@inst("111 0 {C5:5} 1 SS {C4:4}  {args:ri}")
def basic_instruction(C5: BitVector, SS, C4: BitVector, args, _other: BitSection):
    C9 = C5 @ C4
    check(SS in SIZES)
    opcodes = EXPANDED_OPCODES[int(C9)]
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
            opcode_bit_section=C9.bit_section,
            general_bit_section=_other,
        )


dwas = Extension("32bit-address-space", "dwas", (1, 16))
qwas = Extension("64bit-address-space", "qwas", (1, 32))

dwas_or_qwas = ExtensionRequirement(((dwas, qwas),))
qwas_req = ExtensionRequirement.single(qwas)


@inst("111 10 0 00 {dist:8}", set_context={"SS": (0, "h", noreq)})
@inst("111 10 1 00 {addr:8}", set_context={"SS": (0, "h", noreq)})
@inst("111 10 0 01 {dist:16}", set_context={"SS": (1, "x", noreq)})
@inst("111 10 1 01 {addr:16}", set_context={"SS": (1, "x", noreq)})
@inst("111 10 0 10 {dist:32}", set_context={"SS": (2, "d", dwas_or_qwas)})
@inst("111 10 1 10 {addr:32}", set_context={"SS": (2, "d", dwas_or_qwas)})
@inst("111 10 0 11 {dist:64}", set_context={"SS": (3, "q", qwas_req)})
@inst("111 10 1 11 {addr:64}", set_context={"SS": (3, "q", qwas_req)})
def expanded_jump(*, addr=None, dist=None, SS, _other):
    if dist is not None and int(dist) == 0:
        f = Hlt
    else:
        f = CondJump
    yield f(Always(()), label(req=SS[2], rel_target=dist, abs_target=addr), _other, eoc_req)


eoc_and_saf = ExtensionRequirement.single(eoc, saf)


@inst("111 11 0 00 {dist:8}", set_context={"SS": (0, "h", noreq)})
@inst("111 11 1 00 {addr:8}", set_context={"SS": (0, "h", noreq)})
@inst("111 11 0 01 {dist:16}", set_context={"SS": (1, "x", noreq)})
@inst("111 11 1 01 {addr:16}", set_context={"SS": (1, "x", noreq)})
@inst("111 11 0 10 {dist:32}", set_context={"SS": (2, "d", dwas_or_qwas)})
@inst("111 11 1 10 {addr:32}", set_context={"SS": (2, "d", dwas_or_qwas)})
@inst("111 11 0 11 {dist:64}", set_context={"SS": (3, "q", qwas_req)})
@inst("111 11 1 11 {addr:64}", set_context={"SS": (3, "q", qwas_req)})
def expanded_call(*, addr=None, dist=None, SS, _other):
    yield Call(Always(()), label(req=SS[2], rel_target=dist, abs_target=addr), _other, eoc_and_saf)
