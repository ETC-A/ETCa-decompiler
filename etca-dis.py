from argparse import ArgumentParser, FileType

from decoder_lib import disassamble, RenderContext, DecodedInstruction
import extensions


def parse_arguments(args=None):
    parser = ArgumentParser(description="Disassembles a raw binary ROM file with just ETCa assembly")
    parser.add_argument("input_file", type=FileType("rb"))

    return parser.parse_args(args)


def print_instruction(data: bytes, rc: RenderContext, inst: DecodedInstruction):
    start_bit_index = min(inst.bit_section)
    stop_bit_index = max(inst.bit_section)
    assert start_bit_index % 8 == 0, (inst.render(rc), inst.bit_section)
    assert stop_bit_index % 8 == 7, (inst.render(rc), inst.bit_section)
    start_byte_index = start_bit_index // 8
    stop_bit_index = stop_bit_index // 8
    byte: bytes = data[start_byte_index: stop_bit_index + 1]
    print(f"{start_byte_index:04X}: {byte.hex(' ', 2): >9}   {inst.render(rc)}")


def main(args=None):
    options = parse_arguments(args)
    with options.input_file as file:
        data = file.read()
    rc = RenderContext()
    for inst in disassamble(data):
        print_instruction(data, rc, inst)


if __name__ == '__main__':
    main()
