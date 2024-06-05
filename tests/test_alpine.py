import pytest
import sys

from repopulator import *

from .utils import compare_files


@pytest.mark.download(
    'https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/samba-client-4.19.6-r0.apk',
)
def test_one(binaries_path, output_path, expected_path, pki_signer, fixed_datetime, should_populate):
    repo = AlpineRepo('fancy repo')
    package = repo.add_package(binaries_path / 'samba-client-4.19.6-r0.apk')
    assert package.name == 'samba-client'
    assert package.arch == 'x86_64'
    assert package.version_str == '4.19.6-r0'
    assert package.version_key == VersionKey(4, 19, 6, 'r', 0)
    assert package.src_path == binaries_path / 'samba-client-4.19.6-r0.apk'
    assert package.repo_filename == 'samba-client-4.19.6-r0.apk'
    assert package.fields['C'] == 'Q1TXVgzyQiVmY+lk5/cMY6XdPA4CI='
    repo.export(output_path, pki_signer, 'alpine-devel@lists.alpinelinux.org-5261cecb', fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'x86_64/samba-client-4.19.6-r0.apk', binaries_path / 'samba-client-4.19.6-r0.apk')
    if sys.version_info >= (3, 9):
        compare_files(output_path / 'x86_64/APKINDEX.tar.gz', expected_path / 'APKINDEX.tar.gz', should_populate)
    compare_files(output_path / 'expanded/DESCRIPTION', expected_path / 'DESCRIPTION', should_populate)
    compare_files(output_path / 'expanded/x86_64/APKINDEX', expected_path / 'APKINDEX', should_populate)
