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
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/zsm-0.4.0_2~8e79459d43.pkg', 'zsm-0.4.0_2.pkg')
)
def test_one(binaries_path, output_path, expected_path, pki_signer, fixed_datetime, should_populate):
    repo = FreeBSDRepo()
    package = repo.add_package(binaries_path / 'zsm-0.4.0_2.pkg')
    assert package.name == 'zsm'
    assert package.arch == 'freebsd:15:*'
    assert package.version_str == '0.4.0_2'
    assert package.version_key == VersionKey(0, 4, 0, 2)
    assert package.src_path == binaries_path / 'zsm-0.4.0_2.pkg'
    assert package.repo_filename == 'zsm-0.4.0_2.pkg'
    repo.export(output_path, pki_signer, fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'All/zsm-0.4.0_2.pkg', binaries_path / 'zsm-0.4.0_2.pkg')
    compare_files(output_path / 'meta.conf', expected_path / 'meta.conf', should_populate)
    compare_files(output_path / 'meta', expected_path / 'meta', should_populate)
    compare_files(output_path / 'data/data', expected_path / 'data/data', should_populate)
    compare_files(output_path / 'packagesite/packagesite.yaml', expected_path / 'packagesite/packagesite.yaml', should_populate)


@pytest.mark.download(
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/zsm-0.4.0_2~8e79459d43.pkg', 'zsm-0.4.0_2.pkg'),
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/gnustep-app-2.0.0_24~1dd54f3fa8.pkg', 'gnustep-app-2.0.0_24.pkg')
)
def test_two(binaries_path, output_path, expected_path, pki_signer, fixed_datetime, should_populate):
    repo = FreeBSDRepo()
    repo.add_package(binaries_path / 'zsm-0.4.0_2.pkg')
    package = repo.add_package(binaries_path / 'gnustep-app-2.0.0_24.pkg')
    assert package.name == 'gnustep-app'
    assert package.arch == 'freebsd:15:*'
    assert package.version_str == '2.0.0_24'
    assert package.version_key == VersionKey(2, 0, 0, 24)
    assert package.src_path == binaries_path / 'gnustep-app-2.0.0_24.pkg'
    assert package.repo_filename == 'gnustep-app-2.0.0_24.pkg'
    repo.export(output_path, pki_signer, fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'All/gnustep-app-2.0.0_24.pkg', binaries_path / 'gnustep-app-2.0.0_24.pkg')
    compare_files(output_path / 'All/zsm-0.4.0_2.pkg', binaries_path / 'zsm-0.4.0_2.pkg')
    compare_files(output_path / 'meta.conf', expected_path / 'meta.conf', should_populate)
    compare_files(output_path / 'meta', expected_path / 'meta', should_populate)
    compare_files(output_path / 'data/data', expected_path / 'data/data', should_populate)
    compare_files(output_path / 'packagesite/packagesite.yaml', expected_path / 'packagesite/packagesite.yaml', should_populate)

@pytest.mark.download(
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/zsm-0.4.0_2~8e79459d43.pkg', 'zsm-0.4.0_2.pkg'),
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/gnustep-app-2.0.0_24~1dd54f3fa8.pkg', 'gnustep-app-2.0.0_24.pkg'),
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/gnurobots-1.2.0_17~07749feb8d.pkg', 'gnurobots-1.2.0_17.pkg')
)
def test_crud(binaries_path):
    repo = FreeBSDRepo()
    
    package = repo.add_package(binaries_path / 'zsm-0.4.0_2.pkg')
    repo.del_package(package)
    assert [x for x in repo.packages] == []
    repo.del_package(package) # should succeed
    package1 = repo.add_package(binaries_path / 'zsm-0.4.0_2.pkg')
    package2 = repo.add_package(binaries_path / 'gnustep-app-2.0.0_24.pkg')
    repo.del_package(package1)
    assert [x for x in repo.packages] == [package2]

    package1 = repo.add_package(binaries_path / 'zsm-0.4.0_2.pkg')
    package3 = repo.add_package(binaries_path / 'gnurobots-1.2.0_17.pkg')
    
    repo.del_package(package3)
    assert [x for x in repo.packages] == [package2, package1]
    
    repo.del_package(package2)
    assert [x for x in repo.packages] == [package1]

@pytest.mark.download(
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/zsm-0.4.0_2~8e79459d43.pkg', 'zsm-0.4.0_2.pkg'),
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/gnustep-app-2.0.0_24~1dd54f3fa8.pkg', 'gnustep-app-2.0.0_24.pkg'),
    ('https://pkg.freebsd.org/FreeBSD:15:amd64/release_1/All/Hashed/gnurobots-1.2.0_17~07749feb8d.pkg', 'gnurobots-1.2.0_17.pkg')
)
def test_cmd(binaries_path, output_path, pki_cmd):
    subprocess.run([sys.executable, '-m', 'repopulator', 'freebsd'] + 
                    pki_cmd + [
                    '-p', 
                    binaries_path / 'zsm-0.4.0_2.pkg', 
                    binaries_path / 'gnustep-app-2.0.0_24.pkg',
                    binaries_path / 'gnurobots-1.2.0_17.pkg',
                    '-o', output_path
                    ], check=True)
    compare_files(output_path / 'All/zsm-0.4.0_2.pkg', binaries_path / 'zsm-0.4.0_2.pkg')
    compare_files(output_path / 'All/gnustep-app-2.0.0_24.pkg', binaries_path / 'gnustep-app-2.0.0_24.pkg')
    compare_files(output_path / 'All/gnurobots-1.2.0_17.pkg', binaries_path / 'gnurobots-1.2.0_17.pkg')
