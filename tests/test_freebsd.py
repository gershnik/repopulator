# pylint: skip-file

import pytest

from repopulator import *

from .utils import compare_files


@pytest.mark.download(
    'https://pkg.freebsd.org/FreeBSD:13:amd64/release_3/All/zsm-0.4.0.pkg'
)
def test_one(binaries_path, output_path, expected_path, pki_signer, fixed_datetime, should_populate):
    repo = FreeBSDRepo()
    package = repo.add_package(binaries_path / 'zsm-0.4.0.pkg')
    assert package.name == 'zsm'
    assert package.arch == 'freebsd:13:*'
    assert package.version_str == '0.4.0'
    assert package.version_key == VersionKey(0, 4, 0)
    assert package.src_path == binaries_path / 'zsm-0.4.0.pkg'
    assert package.repo_filename == 'zsm-0.4.0.pkg'
    repo.export(output_path, pki_signer, fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'All/zsm-0.4.0.pkg', binaries_path / 'zsm-0.4.0.pkg')
    compare_files(output_path / 'meta.conf', expected_path / 'meta.conf', should_populate)
    compare_files(output_path / 'meta', expected_path / 'meta', should_populate)
    compare_files(output_path / 'data/data', expected_path / 'data/data', should_populate)
    compare_files(output_path / 'packagesite/packagesite.yaml', expected_path / 'packagesite/packagesite.yaml', should_populate)


@pytest.mark.download(
    'https://pkg.freebsd.org/FreeBSD:13:amd64/release_3/All/zsm-0.4.0.pkg',
    'https://pkg.freebsd.org/FreeBSD:13:amd64/release_3/All/gnustep-app-2.0.0_20.pkg'
)
def test_two(binaries_path, output_path, expected_path, pki_signer, fixed_datetime, should_populate):
    repo = FreeBSDRepo()
    repo.add_package(binaries_path / 'zsm-0.4.0.pkg')
    package = repo.add_package(binaries_path / 'gnustep-app-2.0.0_20.pkg')
    assert package.name == 'gnustep-app'
    assert package.arch == 'freebsd:13:*'
    assert package.version_str == '2.0.0_20'
    assert package.version_key == VersionKey(2, 0, 0, 20)
    assert package.src_path == binaries_path / 'gnustep-app-2.0.0_20.pkg'
    assert package.repo_filename == 'gnustep-app-2.0.0_20.pkg'
    repo.export(output_path, pki_signer, fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'All/gnustep-app-2.0.0_20.pkg', binaries_path / 'gnustep-app-2.0.0_20.pkg')
    compare_files(output_path / 'All/zsm-0.4.0.pkg', binaries_path / 'zsm-0.4.0.pkg')
    compare_files(output_path / 'meta.conf', expected_path / 'meta.conf', should_populate)
    compare_files(output_path / 'meta', expected_path / 'meta', should_populate)
    compare_files(output_path / 'data/data', expected_path / 'data/data', should_populate)
    compare_files(output_path / 'packagesite/packagesite.yaml', expected_path / 'packagesite/packagesite.yaml', should_populate)

@pytest.mark.download(
    'https://pkg.freebsd.org/FreeBSD:13:amd64/release_3/All/zsm-0.4.0.pkg',
    'https://pkg.freebsd.org/FreeBSD:13:amd64/release_3/All/gnustep-app-2.0.0_20.pkg',
    'https://pkg.freebsd.org/FreeBSD:13:amd64/release_3/All/gnurobots-1.2.0_17.pkg'
)
def test_crud(binaries_path):
    repo = FreeBSDRepo()
    
    package = repo.add_package(binaries_path / 'zsm-0.4.0.pkg')
    repo.del_package(package)
    assert [x for x in repo.packages] == []
    repo.del_package(package) # should succeed
    package1 = repo.add_package(binaries_path / 'zsm-0.4.0.pkg')
    package2 = repo.add_package(binaries_path / 'gnustep-app-2.0.0_20.pkg')
    repo.del_package(package1)
    assert [x for x in repo.packages] == [package2]

    package1 = repo.add_package(binaries_path / 'zsm-0.4.0.pkg')
    package3 = repo.add_package(binaries_path / 'gnurobots-1.2.0_17.pkg')
    
    repo.del_package(package3)
    assert [x for x in repo.packages] == [package2, package1]
    
    repo.del_package(package2)
    assert [x for x in repo.packages] == [package1]

