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
from lxml import etree

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


def _hash_xml_transformed(path: Path, xslt: etree.XSLT|None) -> str:
    if not path.exists():
        return ''
    if xslt is not None:
        return hashlib.sha256(bytes(xslt(etree.parse(path)))).hexdigest()
    return hash_file(path)

def compare_xml_files(actual: Path, expected: Path, transform: str|None=None, populate_expected: bool=False):
    if not populate_expected:
        assert actual.exists()
        xslt = etree.XSLT(etree.fromstring(transform.encode('utf-8'))) if transform is not None else None
        assert _hash_xml_transformed(actual, xslt) == _hash_xml_transformed(expected, xslt)
    else:
        expected.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(actual, expected)