from dataclasses import dataclass

from decoder_lib import DecodedInstruction, pat, check, IllegalInstruction, DecodedPart, RenderContext, BitSection, \
    Extension, ExtensionRequirement
from extensions.base_isa import Condition, Always, Never

cp = Extension("conditional-prefix", "cp", (1, 4))
cp_req = ExtensionRequirement.single(cp)


@dataclass
class Conditional(DecodedInstruction):
    cond: Condition
    base: DecodedInstruction
    general_bit_section: BitSection

    format_string = "if{cond} {base}"

    def render(self, context: RenderContext) -> str:
        context.push("condition", self.cond)
        base = self.base.render(context)
        context.pop("condition")
        if "used_cond" in context.values:
            context.pop("used_cond")
            return base
        else:
            return super().render(context)

    def get_rendered_arguments(self, context: RenderContext) -> dict[str, str]:
        return {"cond": self.cond.render(context), "base": self.base.render(context)}

    @property
    def atoms(self):
        inner = self.base.atoms
        assert "cond" not in inner
        assert "_general" in inner
        return {"cond": self.cond, **self.base.atoms, '_prefix_cond': ('', self.general_bit_section, cp_req)}


@pat("inst", "1010 {c:cond} {i:inst}")
def conditional_prefix(c, i, _other):
    if isinstance(c, (Always, Never)):
        return
    if any(isinstance(p, Condition) for p in i.atoms):
        raise IllegalInstruction("Can't append a conditional prefix to an instruction that already has a conditional")
    yield Conditional(c, i, _other)
