from extensions.base_isa import BaseIsaOpcodeInfo, BASE_OPCODES

BASE_OPCODES[12].append(BaseIsaOpcodeInfo("pop", "{name}{size}-using {arg1}, {arg2}", has_reg_immediate=False,
                                          extra_check=lambda A, B: B != 6, sign_extend=False,
                                          required_extensions=('stack-and-functions', 'arbitrary-stack-pointer')))

BASE_OPCODES[13].append(BaseIsaOpcodeInfo("push", "{name}{size}-using {arg1}, {arg2}",
                                          extra_check=lambda A, B: A != 6, sign_extend=False,
                                          required_extensions=('stack-and-functions', 'arbitrary-stack-pointer')))
