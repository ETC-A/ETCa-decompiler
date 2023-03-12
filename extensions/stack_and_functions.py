from decoder_lib import pat, label, check, DecodedInstruction, Extension, ExtensionRequirement, inst, DecodedAtom

from .base_isa import BASE_OPCODES, BaseIsaOpcodeInfo, BASE_CONDITIONS, noreq

sad = Extension("stack-and-functions", "sad", (0, 1))
sad_req = ExtensionRequirement.single(sad)

BASE_OPCODES[12].append(BaseIsaOpcodeInfo("pop", "{name}{size} {arg2}", has_reg_immediate=False,
                                          extra_check=lambda A, B: B == 6, sign_extend=False,
                                          required_extensions=sad_req))

BASE_OPCODES[13].append(BaseIsaOpcodeInfo("push", "{name}{size} {arg1}",
                                          extra_check=lambda A, B: A == 6, sign_extend=False,
                                          required_extensions=sad_req))


@inst("10 1 0 1111 {r:reg} 0 CCCC")
def reg_jump(r, CCCC, _other):
    if CCCC == 15:
        yield DecodedInstruction("{opcode} %r{reg}", {
            "opcode": DecodedAtom(CCCC.bit_section, noreq, "special_opcode", "nop"),
            "reg": r
        }, _other, sad_req)
    else:
        con = BASE_CONDITIONS[CCCC]
        if r.value == "7":
            yield DecodedInstruction("{opcode}{con}", {
                "opcode": DecodedAtom(r.bit_section, sad_req, "special_opcode", "ret"),
                "con": DecodedAtom(CCCC.bit_section, noreq, "condition", con),
            }, _other, sad_req)
        else:
            yield DecodedInstruction("{opcode} %r{reg}", {
                "opcode": DecodedAtom(r.bit_section, noreq, "condition_opcode", f"j{con}"),
                "reg": r,
            }, _other, sad_req)


@inst("10 1 0 1111 {r:reg} 1 CCCC")
def reg_call(r, CCCC, _other):
    if CCCC == 15:
        yield DecodedInstruction("{opcode} %r{reg}", {
            "opcode": DecodedAtom(CCCC.bit_section, sad_req, "special_opcode", "nop (call)"),
            "reg": r
        }, _other, sad_req)
    else:
        con = BASE_CONDITIONS[CCCC]
        yield DecodedInstruction("{opcode} %r{reg}", {
            "opcode": DecodedAtom(r.bit_section, sad_req, "condition_opcode", f"call{con}"),
            "reg": r,
        }, _other, sad_req)


@inst("10 1 1 {dest:12}")
def call_rel(dest, _other):
    dest = dest.signed(12)
    yield DecodedInstruction("call {dest}", {
        "dest": label(rel_target=dest)
    }, _other, sad_req)
