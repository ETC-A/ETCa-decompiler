from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, ChainMap
from dataclasses import dataclass, field, InitVar
from typing import Iterable, Callable, Any, TypeAlias, Sequence, ClassVar

from bitarray import bitarray
from bitarray.util import ba2int, hex2ba


class _UnknownInstruction(BaseException):
    pass


class IllegalInstruction(Exception):
    pass


class _NotEnoughBits(Exception):
    pass


BitIndex: TypeAlias = int
BitSection: TypeAlias = Sequence[int]


@dataclass(frozen=True)
class BitVector:
    value: int
    bit_size: int
    bit_section: BitSection = ()

    def unsigned(self, bit_size: int = None):
        if bit_size is None:
            bit_size = self.bit_size
        return BitVector(
            self.value & ((1 << bit_size) - 1),
            bit_size,
            self.bit_section
        )

    def signed(self, bit_size: int = None):
        if bit_size is None:
            bit_size = self.bit_size
        val = self.value & ((1 << bit_size) - 1)
        if val & (1 << (bit_size - 1)):
            val |= -(1 << (bit_size))
        return BitVector(
            val,
            bit_size,
            self.bit_section
        )

    def dec(self, size: int = None):
        if size:
            return f"{self.value:0{size}d}"
        else:
            return str(self.value)

    def __index__(self):
        return self.value

    def __int__(self):
        return self.value

    def __str__(self):
        return f"{self.value:0{self.bit_size}b}"

    def __repr__(self):
        return f"{type(self).__name__}({self.value}, {self.bit_size}, {self.bit_section})"

    def __eq__(self, other):
        if isinstance(other, int):
            return other == self.value
        elif isinstance(other, BitVector):
            return self.value == other.value
        else:
            return False

    def __hash__(self):
        return hash(self.value)

    def __matmul__(self, other):
        if not isinstance(other, BitVector):
            return NotImplemented
        return BitVector(
            (self.value << other.bit_size) | other.value,
            self.bit_size + other.bit_size,
            tuple(self.bit_section) + tuple(other.bit_section)
        )


@dataclass
class RenderContext:
    values: dict[str, DecodedPart] = field(default_factory=dict)

    def push(self, name: str, value: DecodedPart):
        assert name not in self.values
        self.values[name] = value

    def pop(self, name: str):
        assert name in self.values
        self.values.pop(name)


@dataclass(frozen=True)
class Extension:
    name: str
    short: str
    bit: tuple[int, int]


@dataclass(frozen=True)
class ExtensionRequirement:
    extensions: tuple[tuple[Extension, ...], ...]

    def union(*args: ExtensionRequirement):
        required = []
        for a in args:
            for e in a.extensions:
                if len(e) == 1:
                    required.append(e[0])
        choices = []
        for a in args:
            for e in a.extensions:
                if len(e) != 1:
                    if any(o in required for o in e):
                        continue
                    choices.append(e)
        return ExtensionRequirement((*((e,) for e in required), *choices))

    @classmethod
    def single(cls, *args: Extension):
        return ExtensionRequirement(tuple(((a,) for a in args)))


class DecodedPart:
    bit_section: BitSection
    required_extensions: ClassVar[ExtensionRequirement]

    def render(self, context: RenderContext) -> str:
        raise NotImplementedError


@dataclass
class DecodedAtom(DecodedPart):
    bit_section: BitSection
    required_extensions: ExtensionRequirement
    name: str
    value: str | ínt

    def render(self, context: RenderContext) -> str:
        return str(self.value)


@dataclass
class DecodedJumpTarget(DecodedPart):
    bit_section: BitSection
    required_extensions: ExtensionRequirement
    is_relative: bool
    value: BitVector
    instruction_start: BitIndex = None

    def render(self, context: RenderContext) -> str:
        if self.is_relative:
            return f"(rel_target: {self.value.signed().dec()})"
        else:
            return f"(abs_target: {self.value.unsigned().dec()})"

    def target_address(self, inst_address) -> int:
        return inst_address + int(self.value) if self.is_relative else int(self.value)


class DecodedInstruction(DecodedPart, ABC):
    format_string: ClassVar[str]

    def render(self, context: RenderContext) -> str:
        strings = self.get_rendered_arguments(context)
        return self.format_string.format(**strings)

    @abstractmethod
    def get_rendered_arguments(self, context: RenderContext) -> dict[str, str]:
        raise NotImplementedError

    @property
    def bit_section(self):
        return tuple(sorted(set().union(*self._bit_sections)))

    @property
    def required_extensions(self):
        return ExtensionRequirement.union(*self._required_extensions)

    @property
    @abstractmethod
    def atoms(self) -> dict[str, DecodedPart | tuple[str, BitSection, ExtensionRequirement]]:
        return {}

    def edit_atom(self, name: str, value):
        raise TypeError(f"Can't edit instruction {type(self).__name__}")

    @property
    def _bit_sections(self):
        return (p.bit_section if isinstance(p, DecodedPart) else p[1] for p in self.atoms.values())

    @property
    def _required_extensions(self):
        return (p.required_extensions if isinstance(p, DecodedPart) else p[2] for p in self.atoms.values())

    @property
    def start_address(self):
        return min(self.bit_section) // 8


@dataclass
class ParseContext:
    bits: bitarray
    start_i: InitVar[int] = 0
    global_context: ChainMap[str, Any] = field(default_factory=ChainMap)
    bound_values: ChainMap[str, BitVector] = field(default_factory=ChainMap)

    def __post_init__(self, start_i: int):
        self.i = start_i

    def read(self, bit_count: int) -> BitVector:
        if self.i + bit_count > len(self.bits):
            raise _NotEnoughBits((self.i, bit_count, self.bits))
        self.i += bit_count
        return BitVector(ba2int(self.bits[self.i - bit_count:self.i]), bit_count,
                         range(self.i - bit_count, self.i))

    def bind(self, name: str, value: BitVector):
        assert name not in self.bound_values, name
        self.bound_values[name] = value

    @property
    def i(self):
        return self.bound_values.get("__i", 0)

    @i.setter
    def i(self, value):
        self.bound_values["__i"] = value

    @property
    def other_bits(self):
        return self.bound_values.get("__other", ())

    @other_bits.setter
    def other_bits(self, value):
        self.bound_values["__other"] = value

    def add_checkpoint(self):
        self.global_context.maps.insert(0, {})
        self.bound_values.maps.insert(0, {})
        return len(self.bound_values.maps) - 1, len(self.global_context.maps)-1

    def revert(self, cp):
        del self.bound_values.maps[:-cp[0]]
        del self.global_context.maps[:-cp[1]]

    def parse_child(self, target: str):
        pc = ParseContext(self.bits, self.i, self.global_context)
        for r in pc.parse(target):
            cp = self.add_checkpoint()
            self.i = pc.i
            yield r
            self.revert(cp)

    def parse(self, target):
        for p, f in _pattern_register[target]:
            cp = self.add_checkpoint()
            if p.parse(self):
                try:
                    args = {name: value for name, value in self.bound_values.items() if not name.startswith("_")}
                    args.update(
                        {name: value for name, value in self.global_context.items() if not name.startswith("_")})
                    for opt in f(**args, _other=self.other_bits):
                        yield opt
                except _UnknownInstruction:
                    pass
                except IllegalInstruction:
                    raise IllegalInstruction(self.bits)
            self.revert(cp)


class Pattern:
    def parse(self, context: ParseContext) -> bool:
        raise NotImplementedError

    @classmethod
    def from_string(cls, pattern: str, set_context: dict[str, int] = None,
                    req_context: dict[str, int] = None) -> Pattern:
        out = []
        for s in pattern.split():
            if set(s).issubset({'0', '1'}):
                out.append(FixedPattern(len(s), int(s, 2)))
            elif s.isalpha():
                out.append(BoundFixedSize(len(s), s))
            elif s[0] == '{':
                assert s[-1] == '}'
                name, arg = s[1:-1].split(':')
                if arg.isdecimal():
                    size = int(arg)
                    out.append(BoundFixedSize(size, name))
                else:
                    out.append(BoundSubPattern(name, arg))
        if len(out) == 1:
            res = out[0]
        else:
            res = PatternList(out)
        if set_context is not None or req_context is not None:
            res = ContextOperation(res, set_context, req_context)
        return res


@dataclass
class ContextOperation(Pattern):
    base: Pattern
    set_context: dict[str, int]
    req_context: dict[str, int | tuple[int, ...]]

    def parse(self, context: ParseContext) -> bool:
        if self.req_context is not None:
            for name, value in self.req_context:
                if isinstance(value, int):
                    if context.global_context.get(name) != value:
                        return False
                elif context.global_context.get(name) in value:
                    return False
        if self.set_context is not None:
            context.global_context.update(self.set_context)
        return self.base.parse(context)


@dataclass
class FixedPattern(Pattern):
    bit_count: int
    value: int

    def parse(self, context: ParseContext) -> bool:
        if int(context.read(self.bit_count)) == self.value:
            context.other_bits += tuple(range(context.i - self.bit_count, context.i))
            return True
        else:
            return False


@dataclass
class BoundFixedSize(Pattern):
    bit_count: int
    name: str

    def parse(self, context: ParseContext) -> bool:
        val = context.read(self.bit_count)
        context.bind(self.name, val)
        return True


@dataclass
class BoundSubPattern(Pattern):
    name: str
    target: str

    def parse(self, context: ParseContext) -> bool:
        for result in context.parse_child(self.target):
            context.bind(self.name, result)
            return True
        return False


@dataclass
class PatternList(Pattern):
    patterns: list[Pattern]

    def parse(self, context: ParseContext) -> bool:
        cp = context.add_checkpoint()
        for i, p in enumerate(self.patterns):
            try:
                if not p.parse(context):
                    context.revert(cp)
                    return False
                else:
                    pass
            except BaseException as e:
                raise
        return True


def check(cond: int, illegal: bool = False):
    if not cond:
        if illegal:
            raise IllegalInstruction
        else:
            raise _UnknownInstruction


_pattern_register: dict[str, list[tuple[Pattern, Callable]]] = defaultdict(list)


def pat(cat: str, pattern: str, **kwargs):
    def wrapper(f):
        _pattern_register[cat].append((Pattern.from_string(pattern, **kwargs), f))
        return f

    return wrapper


def inst(pattern: str, **kwargs):
    return pat("inst", pattern, **kwargs)


def label(bit_section: BitSection = None, req: ExtensionRequirement = ExtensionRequirement(()), *, rel_target=None,
          abs_target=None):
    if [rel_target, abs_target].count(None) != 1:
        raise TypeError("Exactly one of rel_target, abs_target needs to be given")
    target = rel_target or abs_target
    bit_section = bit_section or target.bit_section
    return DecodedJumpTarget(bit_section, req, (rel_target is not None), target)


def _to_bitarray(bits: bitarray | str | bytes) -> bitarray:
    if isinstance(bits, str):
        bits = hex2ba(bits)
    if isinstance(bits, bytes):
        res = bitarray(endian="big")
        res.frombytes(bits)
        bits = res
    return bits


def decode(bits: bitarray | str | bytes) -> Iterable[DecodedInstruction]:
    """ Returns all possible decodings """
    bits = _to_bitarray(bits)
    any_parse = False
    con = ParseContext(bits)
    for opt in con.parse("inst"):
        opt: DecodedInstruction
        yield opt
        any_parse = True
    if not any_parse:
        raise _UnknownInstruction(bits)


def linear_disassamble(bits: bitarray | str | bytes, start=0) -> Iterable[DecodedInstruction]:
    """ Returns consecutive instructions and will throw an exception at the end """
    bits = _to_bitarray(bits)
    i = start
    while True:
        con = ParseContext(bits, i)
        try:
            inst = next(con.parse("inst"))
        except StopIteration:
            raise _UnknownInstruction(con.i, bits[con.i:con.i + 16], bits[con.i:con.i + 16].tobytes().hex(" ", 2))
        except _NotEnoughBits:
            if con.i == len(bits):
                return
        else:
            i = con.i
            yield inst
