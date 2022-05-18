from decoder_lib import pat, label, check, DecodedInstruction

from .base_isa import BASE_OPCODES, BaseIsaOpcodeInfo, BASE_CONDITIONS

BASE_OPCODES[12].append(BaseIsaOpcodeInfo("pop", "{name}{size} {arg2}", has_reg_immediate=False,
                                          extra_check=lambda A, B: B == 6,
                                          required_extensions=('stack-and-functions',)))

BASE_OPCODES[13].append(BaseIsaOpcodeInfo("push", "{name}{size} {arg1}",
                                          extra_check=lambda A, B: A == 6,
                                          required_extensions=('stack-and-functions',)))


@pat("10 1 0 1111 RRR 0 CCCC")
def reg_jump(RRR, CCCC):
    if CCCC == 15:
        yield DecodedInstruction(f"nop %r{RRR.dec(1)}", ('stack-and-functions',))
    else:
        con = BASE_CONDITIONS[CCCC]
        if RRR == 7:
            yield DecodedInstruction(f"ret{con}", ('stack-and-functions',))
        else:
            yield DecodedInstruction(f"{con} %r{RRR.dec(1)}", ('stack-and-functions',))


@pat("10 1 0 1111 RRR 1 CCCC")
def reg_call(RRR, CCCC):
    if CCCC == 15:
        yield DecodedInstruction(f"nop (call) %r{RRR.dec(1)}", ('stack-and-functions',))
    else:
        con = BASE_CONDITIONS[CCCC]
        yield DecodedInstruction(f"call{con} %r{RRR}", ('stack-and-functions',))


@pat("10 1 1 {dest:12}")
def call_rel(dest):
    dest = dest.signed(12)
    yield DecodedInstruction(f"call {label(rel_target=dest)}", ('stack-and-functions',))
