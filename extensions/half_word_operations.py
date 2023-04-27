from decoder_lib import ExtensionRequirement, Extension
from .base_isa import SIZES

hw = Extension("half-word-operations", "h", (1, 3))

SIZES[0] = ('h', ExtensionRequirement.single(hw))
