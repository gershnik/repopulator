import pytest

from repopulator.rpm import *
from repopulator.rpm import _compareAbiVersion

from .utils import compare_files


def test_compareAbiVersion():
    assert _compareAbiVersion('a', 'a') == 0
    assert _compareAbiVersion('a', 'b') is None
    assert _compareAbiVersion('a(1)', 'a') == 1
    assert _compareAbiVersion('a', 'a(1)') == -1
    assert _compareAbiVersion('a(1)', 'a(1)') == 0
    assert _compareAbiVersion('libc.so.6(GLIBC_2.3.4)(64 bit)', 'libc.so.6(GLIBC_2.3.4)(64 bit)') == 0
    assert _compareAbiVersion('libc.so.6(GLIBC_2.3.4)(64 bit)', 'libc.so.6(GLIBC_2.2.4)(64 bit)') == 1
    assert _compareAbiVersion('libc.so.6(GLIBC_2.1.4)(64 bit)', 'libc.so.6(GLIBC_2.2.4)(64 bit)') == -1
    assert _compareAbiVersion('libc.so.6(GLIBC_2.1.4)(64 bit)', 'libc.so.6()(64 bit)') == 1

@pytest.mark.download(
    "https://download.clearlinux.org/releases/10540/clear/x86_64/os/Packages/sudo-setuid-1.8.17p1-34.x86_64.rpm"
)
def test_one(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = RpmRepo()
    package = repo.addPackage(binaries_path / 'sudo-setuid-1.8.17p1-34.x86_64.rpm')
    assert package.name == 'sudo-setuid'
    assert package.arch == 'x86_64'
    assert package.versionStr == '1.8.17p1-34'
    assert package.versionKey == RpmVersion(('0', '1.8.17p1', '34'))
    repo.export(output_path, pgp_signer, now=fixed_datetime, keepUnzipped=True)
    compare_files(output_path / 'sudo-setuid-1.8.17p1-34.x86_64.rpm', binaries_path / 'sudo-setuid-1.8.17p1-34.x86_64.rpm')
    compare_files(output_path / 'repodata/repomd.xml', expected_path / 'repomd.xml', should_populate)
    compare_files(output_path / 'repodata/primary.xml', expected_path / 'primary.xml', should_populate)
    compare_files(output_path / 'repodata/filelists.xml', expected_path / 'filelists.xml', should_populate)
    compare_files(output_path / 'repodata/other.xml', expected_path / 'other.xml', should_populate)
