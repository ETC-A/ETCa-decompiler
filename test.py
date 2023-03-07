from bitarray import bitarray

from decoder_lib import decode, _NotEnoughBits, RenderContext, _UnknownInstruction
import extensions


def calculated_percent_used(bit_count: int = 8, print_all=True):
    assigned = 0
    for i in range(2 ** bit_count):
        current = 0
        try:
            for res in decode(f"{i:0{bit_count // 4}X}"):
                if print_all:
                    print(f"{i:0{bit_count // 4}X}", res.render(None))
                current += 1
            if current > 1:
                raise ValueError(f"{i:02X}")
            elif current:
                assigned += 1
        except _NotEnoughBits as e:
            pass
        except _UnknownInstruction as e:
            pass
    print(f"{assigned}/{2 ** bit_count} = {assigned / 2 ** bit_count:.2f}")


def decode_print(b: bytes):
    rc = RenderContext()
    for res in decode(b.hex()):
        print(res.render(rc))


# decode_print(bitarray("00 01 1100 000 000 00").tobytes())
# decode_print(bitarray("10 01 0000 000 00000").tobytes())

calculated_percent_used(16)