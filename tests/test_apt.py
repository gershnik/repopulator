import pytest

from pathlib import PurePosixPath
from repopulator import *

from .utils import compare_files


@pytest.mark.download(
    'https://old-releases.ubuntu.com/ubuntu/pool/main/w/wget/wget_1.10-2ubuntu0.1_sparc.deb'
)
def test_one(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = AptRepo()
    dist = repo.addDistribution('blah', origin='some origin', label='some label', suite='hello', 
                                version='1.2', description='hohohoho')
    assert dist.path == PurePosixPath('blah')
    assert dist.origin == 'some origin'
    assert dist.label == 'some label'
    assert dist.suite == 'hello'
    assert dist.version == '1.2'
    assert dist.description == 'hohohoho'
    
    package = repo.addPackage(binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    assert package.name == 'wget'
    assert package.arch == 'sparc'
    assert package.versionStr == '1.10-2ubuntu0.1'
    assert package.versionKey == VersionKey(1, 10, 2, 'ubuntu', 0, 1)
    assert package.srcPath == binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb'
    assert package.repoFilename == 'wget_1.10-2ubuntu0.1_sparc.deb'

    dist.addPackage('main', package)

    assert [x for x in dist.components] == ['main']
    assert [x for x in dist.architectures('main')] == ['sparc']
    assert [x for x in dist.packages('main', 'sparc')] == [package]

    repo.export(output_path, pgp_signer, fixed_datetime)

    compare_files(output_path / 'pool/wget_1.10-2ubuntu0.1_sparc.deb', binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    compare_files(output_path / 'dists/blah/Release', expected_path / 'dists/blah/Release', should_populate)
    compare_files(output_path / 'dists/blah/main/binary-sparc/Packages', expected_path / 'dists/blah/main/binary-sparc/Packages', should_populate)
    compare_files(output_path / 'dists/blah/main/binary-sparc/Packages.gz', expected_path / 'dists/blah/main/binary-sparc/Packages.gz', should_populate)


    