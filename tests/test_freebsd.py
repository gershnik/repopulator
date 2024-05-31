import pytest

from repopulator import *

from .utils import compare_files


@pytest.mark.download(
    'https://pkg.freebsd.org/FreeBSD:13:amd64/release_3/All/zsm-0.4.0.pkg'
)
def test_one(binaries_path, output_path, expected_path, pki_signer, fixed_datetime, should_populate):
    repo = FreeBSDRepo()
    package = repo.addPackage(binaries_path / 'zsm-0.4.0.pkg')
    assert package.name == 'zsm'
    assert package.arch == 'freebsd:13:*'
    assert package.versionStr == '0.4.0'
    assert package.versionKey == VersionKey(0, 4, 0)
    assert package.srcPath == binaries_path / 'zsm-0.4.0.pkg'
    assert package.repoFilename == 'zsm-0.4.0.pkg'
    repo.export(output_path, pki_signer, fixed_datetime, keepExpanded=True)
    compare_files(output_path / 'All/zsm-0.4.0.pkg', binaries_path / 'zsm-0.4.0.pkg')
    compare_files(output_path / 'meta.conf', expected_path / 'meta.conf', should_populate)
    compare_files(output_path / 'meta', expected_path / 'meta', should_populate)
    compare_files(output_path / 'data/data', expected_path / 'data/data', should_populate)
    compare_files(output_path / 'packagesite/packagesite.yaml', expected_path / 'packagesite/packagesite.yaml', should_populate)
