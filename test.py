from bitarray import bitarray

from decoder_lib import decode, _NotEnoughBits
import extensions


def calculated_percent_used(bit_count: int = 8, print_all=True):
    assigned = 0
    for i in range(2 ** bit_count):
        current = 0
        try:
            for res in decode(f"{i:0{bit_count / 4}X}"):
                if print_all:
                    print(f"{i:0{bit_count / 4}X}", res)
                current += 1
            if current > 1:
                raise ValueError(f"{i:02X}")
            elif current:
                assigned += 1
        except _NotEnoughBits as e:
            pass
    print(f"{assigned}/{2 ** bit_count} = {assigned / 2 ** bit_count:.2f}")


def decode_print(b: bytes):
    for res in decode(b.hex()):
        print(b.hex(sep=' ')+ ':', res.with_prefix, res.required_extensions)


decode_print(bitarray("00 01 1100 000 000 00").tobytes())
