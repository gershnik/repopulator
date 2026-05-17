# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

# pylint: skip-file

import hashlib
import shutil
import gzip

from pathlib import Path

from repopulator.util import file_digest

GZIP_MAGIC = b'\x1f\x8b'

def hash_file(path: Path):
    if not path.exists():
        return ''
    with open(path, 'rb') as f:
        if f.read(2) == GZIP_MAGIC:
            f.seek(0)
            with gzip.GzipFile(fileobj=f, mode='rb') as gz:
                return file_digest(gz, hashlib.sha256).hexdigest()
        f.seek(0)
        return file_digest(f, hashlib.sha256).hexdigest()
    
def compare_files(actual: Path, expected: Path, populate_expected: bool=False):
    if not populate_expected:
        assert actual.exists()
        assert hash_file(actual) == hash_file(expected)
    else:
        expected.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(actual, expected)
