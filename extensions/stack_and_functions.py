from decoder_lib import pat, label, check, DecodedInstruction, Extension, ExtensionRequirement, inst, DecodedAtom, \
    RenderContext

from .base_isa import noreq, BasicInstruction, ZeroExtend, TwoReg, RegImm, Nop, Never, CondJump, Always

saf = Extension("stack-and-functions", "saf", (1, 1))
saf_req = ExtensionRequirement.single(saf)


class Pop(TwoReg, ZeroExtend, opcode=12):
    name = "pop"
    format_string = "{opcode}{size} {arg1}"
    required_extensions = saf_req

    @classmethod
    def extra_check(cls, a, b):
        return b.index == 6


class Push(TwoReg, RegImm, ZeroExtend, opcode=13):
    name = "push"
    format_string = "{name}{size} {arg2}"
    required_extensions = saf_req

    @classmethod
    def extra_check(cls, a, b):
        return a.index == 6


class Return(CondJump):
    format_string = "ret{cond}"

    def get_rendered_arguments(self, context: RenderContext) -> dict[str, str]:
        return {
            "cond": "" if isinstance(self.cond, Always) else self.cond.name
        }


@inst("10 1 0 1111 {r:reg} 0 {c:cond}")
def reg_jump(r, c, _other):
    if isinstance(c, Never):
        yield Nop(c, r, _other, saf_req)
    elif r.index == 7:
        yield Return(c, r, _other, saf_req)
    else:
        yield CondJump(c, r, _other, saf_req)


class Call(CondJump):
    format_string = "call{cond} {target}"

    def get_rendered_arguments(self, context: RenderContext) -> dict[str, str]:
        return {
            "cond": "" if isinstance(self.cond, Always) else self.cond.name,
            "target": self.target.render(context)
        }


@inst("10 1 0 1111 {r:reg} 1 {c:cond}")
def reg_call(r, c, _other):
    if isinstance(c, Never):
        pass
    else:
        yield Call(c, r, _other, saf_req)


@inst("10 1 1 {dest:12}")
def call_rel(dest, _other):
    yield Call(Always(()), label(rel_target=dest.signed()), _other, saf_req)
