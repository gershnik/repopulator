import pytest
import sys
import os
from pathlib import Path

from repopulator import *

from .utils import compare_files

@pytest.mark.download(
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst',
    'https://archive.archlinux.org/packages/m/makedumpfile/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig',
    # 'https://archive.archlinux.org/packages/p/pacman/pacman-5.2.2-3-x86_64.pkg.tar.zst',
    # 'https://archive.archlinux.org/packages/p/pacman/pacman-5.2.2-3-x86_64.pkg.tar.zst.sig'
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
