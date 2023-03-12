from decoder_lib import pat


@pat("1100 AA BB")
def expanded_register(AA, BB):
