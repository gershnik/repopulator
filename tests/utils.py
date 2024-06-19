# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

# pylint: skip-file

import hashlib
import shutil

from pathlib import Path

from repopulator.util import file_digest


def hash_file(path: Path):
    if not path.exists():
        return ''
    with open(path, 'rb') as f:
        return file_digest(f, hashlib.sha256).hexdigest()
    
def compare_files(actual: Path, expected: Path, populate_expected: bool=False):
    if not populate_expected:
        assert actual.exists()
        assert hash_file(actual) == hash_file(expected)
    else:
        expected.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(actual, expected)
