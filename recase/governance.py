"""Purpose-specific gates. Legacy self-declared approval flags are insufficient."""
from recase.dataset_control import PURPOSES, permitted

USES = PURPOSES


def approved_for(document, use, review=None):
    return permitted(document, use, review)
