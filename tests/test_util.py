# pylint: skip-file

from repopulator.util import *

def test_lowerBound():
    assert lower_bound([1, 2, 3], 0) == 0
    assert lower_bound([1, 2, 3], 1) == 0
    assert lower_bound([1, 2, 3], 2) == 1
    assert lower_bound([1, 2, 3], 3) == 2
    assert lower_bound([1, 2, 3], 4) == 3