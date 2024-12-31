# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

# pylint: skip-file

import pytest
import sys
import subprocess

from repopulator import *

from .utils import compare_files


@pytest.mark.download(
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/samba-client-4.19.9-r0.apk',
)
def test_one(binaries_path, output_path, expected_path, pki_signer, fixed_datetime, should_populate):
    repo = AlpineRepo('fancy repo')
    package = repo.add_package(binaries_path / 'samba-client-4.19.9-r0.apk')
    assert package.name == 'samba-client'
    assert package.arch == 'x86_64'
    assert package.version_str == '4.19.9-r0'
    assert package.version_key == VersionKey(4, 19, 9, 'r', 0)
    assert package.src_path == binaries_path / 'samba-client-4.19.9-r0.apk'
    assert package.repo_filename == 'samba-client-4.19.9-r0.apk'
    assert package.fields['C'] == 'Q1IZdVsEDSxN0qfNVNB4uePz6O/fY='
    repo.export(output_path, pki_signer, 'alpine-devel@lists.alpinelinux.org-5261cecb', fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'x86_64/samba-client-4.19.9-r0.apk', binaries_path / 'samba-client-4.19.9-r0.apk')
    if sys.version_info >= (3, 9):
        compare_files(output_path / 'x86_64/APKINDEX.tar.gz', expected_path / 'APKINDEX.tar.gz', should_populate)
    compare_files(output_path / 'expanded/DESCRIPTION', expected_path / 'DESCRIPTION', should_populate)
    compare_files(output_path / 'expanded/x86_64/APKINDEX', expected_path / 'APKINDEX', should_populate)

@pytest.mark.download(
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/samba-client-4.19.9-r0.apk',
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/cgdb-0.8.0-r2.apk'
)
def test_two(binaries_path, output_path, expected_path, pki_signer, fixed_datetime, should_populate):
    repo = AlpineRepo('fancy repo')
    repo.add_package(binaries_path / 'samba-client-4.19.9-r0.apk')
    package = repo.add_package(binaries_path / 'cgdb-0.8.0-r2.apk')
    assert package.name == 'cgdb'
    assert package.arch == 'x86_64'
    assert package.version_str == '0.8.0-r2'
    assert package.version_key == VersionKey(0, 8, 0, 'r', 2)
    assert package.src_path == binaries_path / 'cgdb-0.8.0-r2.apk'
    assert package.repo_filename == 'cgdb-0.8.0-r2.apk'
    assert package.fields['C'] == 'Q15n3yDvEce9+/S6laLndWEZsUjfc='
    repo.export(output_path, pki_signer, 'alpine-devel@lists.alpinelinux.org-5261cecb', fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'x86_64/samba-client-4.19.9-r0.apk', binaries_path / 'samba-client-4.19.9-r0.apk')
    compare_files(output_path / 'x86_64/cgdb-0.8.0-r2.apk', binaries_path / 'cgdb-0.8.0-r2.apk')
    if sys.version_info >= (3, 9):
        compare_files(output_path / 'x86_64/APKINDEX.tar.gz', expected_path / 'APKINDEX.tar.gz', should_populate)
    compare_files(output_path / 'expanded/DESCRIPTION', expected_path / 'DESCRIPTION', should_populate)
    compare_files(output_path / 'expanded/x86_64/APKINDEX', expected_path / 'APKINDEX', should_populate)

@pytest.mark.download(
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/samba-client-4.19.9-r0.apk',
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/cgdb-0.8.0-r2.apk',
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/7zip-23.01-r0.apk'
)
def test_crud(binaries_path):
    repo = AlpineRepo('lol')
    
    package = repo.add_package(binaries_path / 'samba-client-4.19.9-r0.apk')
    repo.del_package(package)
    assert [x for x in repo.architectures] == []
    repo.del_package(package) # should succeed
    package1 = repo.add_package(binaries_path / 'samba-client-4.19.9-r0.apk')
    package2 = repo.add_package(binaries_path / 'cgdb-0.8.0-r2.apk')
    repo.del_package(package1)
    assert [x for x in repo.packages('x86_64')] == [package2]

    package1 = repo.add_package(binaries_path / 'samba-client-4.19.9-r0.apk')
    package3 = repo.add_package(binaries_path / '7zip-23.01-r0.apk')
    
    repo.del_package(package3)
    assert [x for x in repo.architectures] == ['x86_64']
    assert [x for x in repo.packages('x86_64')] == [package2, package1]
    
    repo.del_package(package2)
    assert [x for x in repo.packages('x86_64')] == [package1]

@pytest.mark.download(
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/samba-client-4.19.9-r0.apk',
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/cgdb-0.8.0-r2.apk',
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/7zip-23.01-r0.apk'
)
def test_cmd(binaries_path, output_path, pki_cmd):
    subprocess.run([sys.executable, '-m', 'repopulator', 'alpine',
                    '-d', 'myrepo'] + pki_cmd + ['-s', 'alpine-devel@lists.alpinelinux.org-5261cecb',
                    '-p', binaries_path / 'samba-client-4.19.9-r0.apk', 
                    binaries_path / 'cgdb-0.8.0-r2.apk',
                    binaries_path / '7zip-23.01-r0.apk',
                    '-o', output_path
                    ], check=True)
    compare_files(output_path / 'x86_64/samba-client-4.19.9-r0.apk', binaries_path / 'samba-client-4.19.9-r0.apk')
    compare_files(output_path / 'x86_64/cgdb-0.8.0-r2.apk', binaries_path / 'cgdb-0.8.0-r2.apk')
    compare_files(output_path / 'aarch64/7zip-23.01-r0.apk', binaries_path / '7zip-23.01-r0.apk')
    