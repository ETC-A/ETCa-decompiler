from decoder_lib import pat, inst


@inst("1100 0 A B X {base:inst}", set_context={"Q": 0})
@inst("1100 1 A B X {base:inst}", set_context={"Q": 1})
def expanded_register(A, B, X, base, _other, Q):
    print(A, B, X, base, Q)
    yield base
