from decoder_lib import Extension, ExtensionRequirement
from .base_isa import SIZES

qw = Extension("quad-word-operations", "q", (0, 15))

SIZES[3] = ('q', ExtensionRequirement.single(qw))
