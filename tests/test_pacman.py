import pytest
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
    package = repo.addPackage(binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    assert package.name == 'makedumpfile'
    assert package.arch == 'x86_64'
    assert package.versionStr == '1.7.1-1'
    assert package.versionKey == VersionKey(1, 7, 1, 1)
    assert package.srcPath == binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst'
    assert package.sigPath == binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig'
    assert package.repoFilename == 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst'
    repo.export(output_path, pgp_signer, fixed_datetime, keepExpanded=True)
    compare_files(output_path / 'x86_64/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst', binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst')
    compare_files(output_path / 'x86_64/makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig', binaries_path / 'makedumpfile-1.7.1-1-x86_64.pkg.tar.zst.sig')
    compare_files(output_path / 'x86_64/fancyrepo.db.tar.gz', expected_path / 'fancyrepo.db.tar.gz', should_populate)
    compare_files(output_path / 'x86_64/fancyrepo.files.tar.gz', expected_path / 'fancyrepo.files.tar.gz', should_populate)
    assert (output_path / 'x86_64/fancyrepo.db').is_symlink()
    assert (output_path / 'x86_64/fancyrepo.db').readlink() == Path('fancyrepo.db.tar.gz')
    assert (output_path / 'x86_64/fancyrepo.db.sig').is_symlink()
    assert (output_path / 'x86_64/fancyrepo.db.sig').readlink() == Path('fancyrepo.db.tar.gz.sig')
    assert (output_path / 'x86_64/fancyrepo.files').is_symlink()
    assert (output_path / 'x86_64/fancyrepo.files').readlink() == Path('fancyrepo.files.tar.gz')
    assert (output_path / 'x86_64/fancyrepo.files.sig').is_symlink()
    assert (output_path / 'x86_64/fancyrepo.files.sig').readlink() == Path('fancyrepo.files.tar.gz.sig')
