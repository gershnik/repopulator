import pytest

from pathlib import PurePosixPath
from repopulator import *

from .utils import compare_files


@pytest.mark.download(
    'https://old-releases.ubuntu.com/ubuntu/pool/main/w/wget/wget_1.10-2ubuntu0.1_sparc.deb'
)
def test_one(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = AptRepo()
    dist = repo.add_distribution('blah', origin='some origin', label='some label', suite='hello', 
                                version='1.2', description='hohohoho')
    assert dist.path == PurePosixPath('blah')
    assert dist.origin == 'some origin'
    assert dist.label == 'some label'
    assert dist.suite == 'hello'
    assert dist.version == '1.2'
    assert dist.description == 'hohohoho'
    
    package = repo.add_package(binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    assert package.name == 'wget'
    assert package.arch == 'sparc'
    assert package.version_str == '1.10-2ubuntu0.1'
    assert package.version_key == VersionKey(1, 10, 2, 'ubuntu', 0, 1)
    assert package.src_path == binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb'
    assert package.repo_filename == 'wget_1.10-2ubuntu0.1_sparc.deb'

    repo.assign_package(package, dist, component='main')

    assert [x for x in dist.components] == ['main']
    assert [x for x in dist.architectures('main')] == ['sparc']
    assert [x for x in dist.packages('main', 'sparc')] == [package]

    repo.export(output_path, pgp_signer, fixed_datetime)

    compare_files(output_path / 'pool/wget_1.10-2ubuntu0.1_sparc.deb', binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    compare_files(output_path / 'dists/blah/Release', expected_path / 'dists/blah/Release', should_populate)
    compare_files(output_path / 'dists/blah/main/binary-sparc/Packages', expected_path / 'dists/blah/main/binary-sparc/Packages', should_populate)
    compare_files(output_path / 'dists/blah/main/binary-sparc/Packages.gz', expected_path / 'dists/blah/main/binary-sparc/Packages.gz', should_populate)


@pytest.mark.download(
    'https://old-releases.ubuntu.com/ubuntu/pool/main/w/wget/wget_1.10-2ubuntu0.1_sparc.deb',
    'https://old-releases.ubuntu.com/ubuntu/pool/main/n/nano/nano-udeb_1.3.10-1_amd64.udeb'
)
def test_two(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = AptRepo()
    dist = repo.add_distribution('blah/xyz', origin='some origin', label='some label', suite='hello', 
                                version='3.5', description='hohohoho')
    package1 = repo.add_package(binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    package2 = repo.add_package(binaries_path / 'nano-udeb_1.3.10-1_amd64.udeb')
    assert package2.name == 'nano-udeb'
    assert package2.arch == 'amd64'
    assert package2.version_str == '1.3.10-1'
    assert package2.version_key == VersionKey(1, 3, 10, 1)
    assert package2.src_path == binaries_path / 'nano-udeb_1.3.10-1_amd64.udeb'
    assert package2.repo_filename == 'nano-udeb_1.3.10-1_amd64.udeb'

    repo.assign_package(package1, dist, component='main')
    repo.assign_package(package2, dist, component='main')

    assert [x for x in dist.components] == ['main']
    assert [x for x in dist.architectures('main')] == ['sparc', 'amd64']
    assert [x for x in dist.packages('main', 'sparc')] == [package1]
    assert [x for x in dist.packages('main', 'amd64')] == [package2]

    repo.export(output_path, pgp_signer, fixed_datetime)

    compare_files(output_path / 'pool/wget_1.10-2ubuntu0.1_sparc.deb', binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    compare_files(output_path / 'pool/nano-udeb_1.3.10-1_amd64.udeb', binaries_path / 'nano-udeb_1.3.10-1_amd64.udeb')
    compare_files(output_path / 'dists/blah/xyz/Release', expected_path / 'dists/blah/xyz/Release', should_populate)
    compare_files(output_path / 'dists/blah/xyz/main/binary-sparc/Packages', expected_path / 'dists/blah/xyz/main/binary-sparc/Packages', should_populate)
    compare_files(output_path / 'dists/blah/xyz/main/binary-sparc/Packages.gz', expected_path / 'dists/blah/xyz/main/binary-sparc/Packages.gz', should_populate)
    compare_files(output_path / 'dists/blah/xyz/main/binary-amd64/Packages', expected_path / 'dists/blah/xyz/main/binary-amd64/Packages', should_populate)
    compare_files(output_path / 'dists/blah/xyz/main/binary-amd64/Packages.gz', expected_path / 'dists/blah/xyz/main/binary-amd64/Packages.gz', should_populate)

@pytest.mark.download(
    'https://old-releases.ubuntu.com/ubuntu/pool/main/w/wget/wget_1.10-2ubuntu0.1_sparc.deb',
    'https://old-releases.ubuntu.com/ubuntu/pool/main/w/wget/wget_1.10.2-1ubuntu1.2_sparc.deb'
)
def test_two_close(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = AptRepo()
    dist = repo.add_distribution('blah', origin='some origin', label='some label', suite='hello', 
                                version='3.5', description='hohohoho')
    package1 = repo.add_package(binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    package2 = repo.add_package(binaries_path / 'wget_1.10.2-1ubuntu1.2_sparc.deb')
    assert package2.name == 'wget'
    assert package2.arch == 'sparc'
    assert package2.version_str == '1.10.2-1ubuntu1.2'
    assert package2.version_key == VersionKey(1, 10, 2, 1, 'ubuntu', 1, 2)
    assert package2.src_path == binaries_path / 'wget_1.10.2-1ubuntu1.2_sparc.deb'
    assert package2.repo_filename == 'wget_1.10.2-1ubuntu1.2_sparc.deb'

    repo.assign_package(package1, dist, component='main')
    repo.assign_package(package2, dist, component='main')

    assert [x for x in dist.components] == ['main']
    assert [x for x in dist.architectures('main')] == ['sparc']
    assert [x for x in dist.packages('main', 'sparc')] == [package1, package2]

    repo.export(output_path, pgp_signer, fixed_datetime)

    compare_files(output_path / 'pool/wget_1.10-2ubuntu0.1_sparc.deb', binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    compare_files(output_path / 'pool/wget_1.10.2-1ubuntu1.2_sparc.deb', binaries_path / 'wget_1.10.2-1ubuntu1.2_sparc.deb')
    compare_files(output_path / 'dists/blah/Release', expected_path / 'dists/blah/Release', should_populate)
    compare_files(output_path / 'dists/blah/main/binary-sparc/Packages', expected_path / 'dists/blah/main/binary-sparc/Packages', should_populate)
    compare_files(output_path / 'dists/blah/main/binary-sparc/Packages.gz', expected_path / 'dists/blah/main/binary-sparc/Packages.gz', should_populate)
    
@pytest.mark.download(
    'https://old-releases.ubuntu.com/ubuntu/pool/main/w/wget/wget_1.10-2ubuntu0.1_sparc.deb',
    'https://old-releases.ubuntu.com/ubuntu/pool/main/w/wget/wget_1.10.2-1ubuntu1.2_sparc.deb',
    'https://old-releases.ubuntu.com/ubuntu/pool/main/n/nano/nano-udeb_1.3.10-1_amd64.udeb'
)
def test_crud(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = AptRepo()
    dist = repo.add_distribution('blah', origin='some origin', label='some label', suite='hello', 
                                version='3.5', description='hohohoho')
    assert [x for x in repo.distributions] == [dist]
    repo.del_distribution(dist)
    assert [x for x in repo.distributions] == []
    repo.del_distribution(dist) # should be ignored
    dist1 = repo.add_distribution('blah', origin='some origin', label='some label', suite='hello', 
                                version='3.5', description='hohohoho')
    dist2 = repo.add_distribution('another', origin='some origin', label='some label', suite='hello', 
                                version='3.5', description='hohohoho')
    assert repo.distributions == set((dist1, dist2))
    repo.del_distribution(dist1)
    assert [x for x in repo.distributions] == [dist2]

    package = repo.add_package(binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    repo.del_package(package)
    assert [x for x in repo.packages] == []
    repo.del_package(package) # should succeed
    package1 = repo.add_package(binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    package2 = repo.add_package(binaries_path / 'nano-udeb_1.3.10-1_amd64.udeb')
    repo.del_package(package1)
    assert [x for x in repo.packages] == [package2]

    package1 = repo.add_package(binaries_path / 'wget_1.10-2ubuntu0.1_sparc.deb')
    package3 = repo.add_package(binaries_path / 'wget_1.10.2-1ubuntu1.2_sparc.deb')

    repo.assign_package(package1, dist2, 'hello')
    repo.unassign_package(package1, dist2, 'hello')
    assert [x for x in dist2.components] == []
    repo.assign_package(package1, dist2, 'hello')
    repo.assign_package(package2, dist2, 'hello')
    repo.assign_package(package3, dist2, 'hello')
    repo.unassign_package(package1, dist2, 'hello')
    assert [x for x in dist2.packages('hello', 'amd64')] == [package2]
    assert [x for x in dist2.packages('hello', 'sparc')] == [package3]

    repo.del_package(package2)
    assert [x for x in dist2.architectures('hello')] == ['sparc']



    
