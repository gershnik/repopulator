# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

# pylint: skip-file

import pytest
import sys
import os
import subprocess

from repopulator import *

from .utils import compare_files

@pytest.mark.download(
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig',
)
def test_one(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = PacmanRepo('fancyrepo')
    package = repo.add_package(binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    assert package.name == 'makedumpfile'
    assert package.arch == 'x86_64'
    assert package.version_str == '1.7.1-1'
    assert package.version_key == VersionKey(1, 7, 1, 1)
    assert package.src_path == binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst'
    assert package.sig_path == binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig'
    assert package.repo_filename == 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst'
    repo.export(output_path, pgp_signer, fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'x86_64/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst', binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    compare_files(output_path / 'x86_64/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig', binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig')
    if sys.version_info >= (3, 9):
        compare_files(output_path / 'x86_64/fancyrepo.db.tar.gz', expected_path / 'fancyrepo.db.tar.gz', should_populate)
        compare_files(output_path / 'x86_64/fancyrepo.files.tar.gz', expected_path / 'fancyrepo.files.tar.gz', should_populate)
    compare_files(output_path / 'expanded/x86_64/fancyrepo.db/makedumpfile-1.7.1-1/desc', expected_path / 'desc', should_populate)
    compare_files(output_path / 'expanded/x86_64/fancyrepo.files/makedumpfile-1.7.1-1/files', expected_path / 'files', should_populate)
    assert (output_path / 'x86_64/fancyrepo.db').is_symlink()
    assert os.readlink(output_path / 'x86_64/fancyrepo.db') == 'fancyrepo.db.tar.gz'
    assert (output_path / 'x86_64/fancyrepo.db.sig').is_symlink()
    assert os.readlink(output_path / 'x86_64/fancyrepo.db.sig') == 'fancyrepo.db.tar.gz.sig'
    assert (output_path / 'x86_64/fancyrepo.files').is_symlink()
    assert os.readlink(output_path / 'x86_64/fancyrepo.files') == 'fancyrepo.files.tar.gz'
    assert (output_path / 'x86_64/fancyrepo.files.sig').is_symlink()
    assert os.readlink(output_path / 'x86_64/fancyrepo.files.sig') == 'fancyrepo.files.tar.gz.sig'

@pytest.mark.download(
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig',
    'https://archive.archlinux.org/packages/p/pacman/pacman-5.2.2-3-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/p/pacman/pacman-5.2.2-3-x86_64.pkg.tar.zst.sig'
)
def test_two(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = PacmanRepo('fancyrepo')
    repo.add_package(binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    package = repo.add_package(binaries_path / 'pacman-5.2.2-3-x86_64.pkg.tar.zst')
    assert package.name == 'pacman'
    assert package.arch == 'x86_64'
    assert package.version_str == '5.2.2-3'
    assert package.version_key == VersionKey(5, 2, 2, 3)
    assert package.src_path == binaries_path / 'pacman-5.2.2-3-x86_64.pkg.tar.zst'
    assert package.repo_filename == 'pacman-5.2.2-3-x86_64.pkg.tar.zst'
    repo.export(output_path, pgp_signer, fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'x86_64/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst', binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    compare_files(output_path / 'x86_64/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig', binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig')
    compare_files(output_path / 'x86_64/pacman-5.2.2-3-x86_64.pkg.tar.zst', binaries_path / 'pacman-5.2.2-3-x86_64.pkg.tar.zst')
    compare_files(output_path / 'x86_64/pacman-5.2.2-3-x86_64.pkg.tar.zst.sig', binaries_path / 'pacman-5.2.2-3-x86_64.pkg.tar.zst.sig')
    if sys.version_info >= (3, 9):
        compare_files(output_path / 'x86_64/fancyrepo.db.tar.gz', expected_path / 'fancyrepo.db.tar.gz', should_populate)
        compare_files(output_path / 'x86_64/fancyrepo.files.tar.gz', expected_path / 'fancyrepo.files.tar.gz', should_populate)
    assert (output_path / 'x86_64/fancyrepo.db').is_symlink()
    assert os.readlink(output_path / 'x86_64/fancyrepo.db') == 'fancyrepo.db.tar.gz'
    assert (output_path / 'x86_64/fancyrepo.db.sig').is_symlink()
    assert os.readlink(output_path / 'x86_64/fancyrepo.db.sig') == 'fancyrepo.db.tar.gz.sig'
    assert (output_path / 'x86_64/fancyrepo.files').is_symlink()
    assert os.readlink(output_path / 'x86_64/fancyrepo.files') == 'fancyrepo.files.tar.gz'
    assert (output_path / 'x86_64/fancyrepo.files.sig').is_symlink()
    assert os.readlink(output_path / 'x86_64/fancyrepo.files.sig') == 'fancyrepo.files.tar.gz.sig'


@pytest.mark.download(
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig',
    'https://archive.archlinux.org/packages/p/pacman/pacman-5.2.2-3-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/p/pacman/pacman-5.2.2-3-x86_64.pkg.tar.zst.sig',
    'https://archive.archlinux.org/packages/t/tar/tar-1.34-1-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/t/tar/tar-1.34-1-x86_64.pkg.tar.zst.sig'
)
def test_crud(binaries_path):
    repo = PacmanRepo('lol')
    
    package = repo.add_package(binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    repo.del_package(package)
    assert [x for x in repo.architectures] == []
    repo.del_package(package) # should succeed
    package1 = repo.add_package(binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    package2 = repo.add_package(binaries_path / 'pacman-5.2.2-3-x86_64.pkg.tar.zst')
    repo.del_package(package1)
    assert [x for x in repo.packages('x86_64')] == [package2]

    package1 = repo.add_package(binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    package3 = repo.add_package(binaries_path / 'tar-1.34-1-x86_64.pkg.tar.zst')
    
    repo.del_package(package3)
    assert [x for x in repo.architectures] == ['x86_64']
    assert [x for x in repo.packages('x86_64')] == [package1, package2]
    
    repo.del_package(package2)
    assert [x for x in repo.packages('x86_64')] == [package1]

@pytest.mark.download(
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig',
    'https://archive.archlinux.org/packages/p/pacman/pacman-5.2.2-3-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/p/pacman/pacman-5.2.2-3-x86_64.pkg.tar.zst.sig',
    'https://archive.archlinux.org/packages/t/tar/tar-1.34-1-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/t/tar/tar-1.34-1-x86_64.pkg.tar.zst.sig'
)
def test_cmd(binaries_path, output_path, pgp_cmd):
    subprocess.run([sys.executable, '-m', 'repopulator', 'pacman',
                    '-n', 'myrepo'] + pgp_cmd + [
                    '-p', 
                    binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst', 
                    binaries_path / 'pacman-5.2.2-3-x86_64.pkg.tar.zst',
                    binaries_path / 'tar-1.34-1-x86_64.pkg.tar.zst',
                    '-o', output_path
                    ], check=True)
    compare_files(output_path / 'x86_64/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst', binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    compare_files(output_path / 'x86_64/pacman-5.2.2-3-x86_64.pkg.tar.zst', binaries_path / 'pacman-5.2.2-3-x86_64.pkg.tar.zst')
    compare_files(output_path / 'x86_64/tar-1.34-1-x86_64.pkg.tar.zst', binaries_path / 'tar-1.34-1-x86_64.pkg.tar.zst')
