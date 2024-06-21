# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

# pylint: skip-file

from repopulator.util import *

def test_lowerBound():
    assert lower_bound([1, 2, 3], 0) == 0
    assert lower_bound([1, 2, 3], 1) == 0
    assert lower_bound([1, 2, 3], 2) == 1
    assert lower_bound([1, 2, 3], 3) == 2
    assert lower_bound([1, 2, 3], 4) == 3