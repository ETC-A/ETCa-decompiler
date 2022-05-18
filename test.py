from decoder_lib import decode
import extensions

assigned = 0
for i in range(2 ** 16):
    current = 0
    for res in decode(f"{i:04X}"):
        print(f"{i:04X}", res)
        current += 1
    if current > 1:
        raise ValueError(f"{i:04X}")
    elif current:
        assigned += 1

print(f"{assigned}/{2 ** 16} = {assigned / 2 ** 16:.2f}")
