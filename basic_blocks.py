from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from bitarray import bitarray

from decoder_lib import DecodedInstruction, _to_bitarray, linear_disassamble, DecodedJumpTarget
from extensions.base_isa import Hlt, CondJump, Always, Never
from extensions.stack_and_functions import Call


@dataclass
class BasicBlock:
    start_address: int
    instructions: list[DecodedInstruction]
    targets: list[BasicBlock]


def is_end(inst):
    match inst:
        case Call(Always()):
            return False
        case CondJump(Always()) | Hlt(Always()):
            return True
        case _:
            return False


def jump_targets(inst) -> Iterable[DecodedJumpTarget]:
    match inst:
        case Hlt():
            pass
        case CondJump(cond, label) if not isinstance(cond, Never):
            yield label


def nonlinear_disassemble(bits: bitarray | str | bytes, start=0, log=None) -> list[BasicBlock]:
    bits = _to_bitarray(bits)
    out = BasicBlock(start, [], [])
    done = []
    queue = [out]
    basic_blocks = {}
    while queue:
        bb = min(queue, key=lambda bb: bb.start_address)
        queue.remove(bb)
        assert not bb.instructions
        print(hex(bb.start_address))

        for inst in linear_disassamble(bits, 8 * bb.start_address):
            if log is not None:
                log(inst)
            if inst.start_address in basic_blocks and basic_blocks[inst.start_address] is not bb:
                other = basic_blocks[inst.start_address]
                assert bb.start_address < other.start_address, (bb, other)
                assert not other.instructions
                queue.remove(other)
            basic_blocks[inst.start_address] = bb
            bb.instructions.append(inst)
            for target in jump_targets(inst):
                if not isinstance(target, DecodedJumpTarget):
                    continue
                target = target.target_address(inst.start_address)
                if target not in basic_blocks:
                    t = BasicBlock(target, [], [])
                    basic_blocks[target] = t
                    queue.append(t)
                bb.targets.append(basic_blocks[target])
            if is_end(inst):
                break
        done.append(bb)
    return done
