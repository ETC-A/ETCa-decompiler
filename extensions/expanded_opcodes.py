from decoder_lib import pat, DecodedInstruction, label, check
from .base_isa import BaseIsaOpcodeInfo, SIZES

EXPANDED_OPCODES = {
    0: [BaseIsaOpcodeInfo("adc")],
    1: [BaseIsaOpcodeInfo("sbb")],
    2: [BaseIsaOpcodeInfo("rsbb")]
}


@pat("111 0 {C5:5} 0 SS {C4:4} AAA BBB 00")
def expanded_reg_reg(C5, SS, C4, AAA, BBB):
    opcode = C5 @ C4
    check(SS in SIZES)
    opcodes = EXPANDED_OPCODES.get(opcode, [])
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
                                 (*SIZES[SS][1], "expanded-opcodes", *opcode.required_extensions))


@pat("111 0 {C5:5} 1 SS {C4:4} AAA IIIII")
def expanded_reg_immediate(C5, SS, C4, AAA, IIIII):
    check(SS in SIZES)
    opcode = C5 @ C4
    opcodes = EXPANDED_OPCODES.get(opcode, [])
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
                                 (*SIZES[SS][1], "expanded-opcodes", *opcode.required_extensions))
