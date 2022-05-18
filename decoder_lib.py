from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Callable

from bitarray import bitarray
from bitarray.util import ba2int, hex2ba


class _UnknownInstruction(BaseException):
    pass


class _IllegalInstruction(Exception):
    pass


class _NotEnoughBits(Exception):
    pass


class ResultInt(int):
    def unsigned(self, bit_size: int):
        return ResultInt(self & ((1 << bit_size) - 1), bit_size)

    def signed(self, bit_size: int = None):
        if bit_size is None:
            bit_size = self.bit_size
        val = self & ((1 << bit_size) - 1)
        if val & (1 << (bit_size - 1)):
            val |= -(1 << (bit_size))
        return ResultInt(val, bit_size)

    def dec(self, size: int = None):
        if size:
            return f"{self.value:0{size}d}"
        else:
            return str(self.value)

    def __str__(self):
        return f"{self.value:0{self.bit_size}b}"

    def __repr__(self):
        return f"{type(self).__name__}({self.value}, {self.bit_size})"

    def __new__(cls, value, bit_size):
        out = super(ResultInt, cls).__new__(cls, value)
        out.value = int(value)
        out.bit_size = bit_size
        return out

    def __matmul__(self, other):
        if not isinstance(other, ResultInt):
            return NotImplemented
        return ResultInt((self.value << other.bit_size) | other.value, self.bit_size + other.bit_size)

    def __rmatmul__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        assert other >= 0, other
        return ResultInt((other << self.bit_size) | self.value, self.bit_size + other.bit_length())


@dataclass
class DecodedInstruction:
    assembly: str
    required_extensions: tuple[str, ...]
    is_prefix: bool = False
    prefix_list: list[DecodedInstruction] = field(default_factory=list)

    @property
    def with_prefix(self):
        return " ".join([i.assembly for i in (*self.prefix_list, self)])


@dataclass
class ParseContext:
    bits: bitarray
    i: int = 0
    bound_values: dict[str, int] = field(default_factory=dict)

    def read(self, bit_count: int) -> ResultInt:
        if self.i + bit_count > len(self.bits):
            raise _NotEnoughBits((self.i, bit_count, self.bits))
        self.i += bit_count
        return ResultInt(ba2int(self.bits[self.i - bit_count:self.i]), bit_count)

    def bind(self, name: str, value: int):
        assert name not in self.bound_values, name
        self.bound_values[name] = value


class Pattern:
    def parse(self, context: ParseContext) -> bool:
        raise NotImplementedError

    @classmethod
    def from_string(cls, pattern: str) -> Pattern:
        out = []
        for s in pattern.split():
            if set(s).issubset({'0', '1'}):
                out.append(FixedPattern(len(s), int(s, 2)))
            elif s.isalpha():
                out.append(BoundFixedSize(len(s), s))
            elif s[0] == '{':
                assert s[-1] == '}'
                name, size = s[1:-1].split(':')
                if size.isdigit():
                    size = int(size)
                    out.append(BoundFixedSize(size, name))
                else:
                    out.append(BoundDynamicSize(size, name))
        if len(out) == 1:
            return out[0]
        else:
            return PatternList(out)


@dataclass
class FixedPattern(Pattern):
    bit_count: int
    value: int

    def parse(self, context: ParseContext) -> bool:
        return context.read(self.bit_count) == self.value


@dataclass
class BoundFixedSize(Pattern):
    bit_count: int
    name: str

    def parse(self, context: ParseContext) -> bool:
        val = context.read(self.bit_count)
        context.bind(self.name, val)
        return True


@dataclass
class BoundDynamicSize(Pattern):
    size_expr: str
    name: str

    def parse(self, context: ParseContext) -> bool:
        bit_count = eval(self.size_expr, {}, context.bound_values)
        val = context.read(bit_count)
        context.bind(self.name, val)
        return True


@dataclass
class PatternList(Pattern):
    patterns: list[Pattern]

    def parse(self, context: ParseContext) -> bool:
        for i,p in enumerate(self.patterns):
            try:
                if not p.parse(context):
                    # print(f"Failed {i}/{len(self.patterns)}", p, context)
                    return False
                else:
                    # print(f"Success {i}/{len(self.patterns)}", p, context)
                    pass
            except BaseException as e:
                # print(f"Exception {i}/{len(self.patterns)}", p, e)
                raise
        return True


def check(cond: int, illegal: bool = False):
    if not cond:
        if illegal:
            raise _IllegalInstruction
        else:
            raise _UnknownInstruction


_pattern_register: list[tuple[Pattern, Callable]] = []


def pat(pattern: str):
    def wrapper(f):
        _pattern_register.append((Pattern.from_string(pattern), f))
        return f

    return wrapper


def label(*, rel_target=None, abs_target=None):
    if [rel_target, abs_target].count(None) != 1:
        raise TypeError("Exactly one of rel_target, abs_target needs to be given")
    if rel_target is not None:
        return f"(rel_target: {rel_target.dec()})"
    elif abs_target is not None:
        return f"(abs_target: {abs_target.dec()})"
    else:
        assert False, "Unreachable"


def decode(bits: bitarray | str, prefix: list[DecodedInstruction] = None) -> Iterable[DecodedInstruction]:
    prefix = prefix or []
    if isinstance(bits, str):
        bits = hex2ba(bits)
    for p, f in _pattern_register:
        con = ParseContext(bits)
        if p.parse(con):
            try:
                for opt in f(**con.bound_values):
                    opt: DecodedInstruction
                    if opt.is_prefix:
                        remaining = con.bits[con.i:]
                        try:
                            yield from decode(remaining, [*opt.prefix_list, opt])
                        except _NotEnoughBits:
                            opt.prefix_list = prefix + opt.prefix_list
                            yield opt
                    else:
                        opt.prefix_list = prefix + opt.prefix_list
                        yield opt
            except _UnknownInstruction:
                continue
            except _IllegalInstruction:
                raise _IllegalInstruction(bits)
