from decoder_lib import DecodedInstruction, pat, check
from extensions.base_isa import BASE_CONDITIONS


@pat("1010 CCCC")
def conditional_prefix(CCCC):
    check(CCCC not in (14, 15))
    yield DecodedInstruction(f"if{BASE_CONDITIONS[CCCC]}", ("conditional-prefix",), True)
