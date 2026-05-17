# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

# pylint: skip-file

import pytest
import sys
import subprocess

from repopulator import RpmRepo, RpmVersion
from repopulator.rpm import _compare_abi_version

from .utils import compare_files, compare_xml_files

REPOMD_NORMALIZE = """\
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:repo="http://linux.duke.edu/metadata/repo">
  <xsl:output method="xml" indent="no"/>
  <xsl:template match="@*|node()">
    <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
  </xsl:template>
  <xsl:template match="repo:data[substring(repo:location/@href, string-length(repo:location/@href) - 2) = '.gz']/repo:checksum/text()"/>
  <xsl:template match="repo:data[substring(repo:location/@href, string-length(repo:location/@href) - 2) = '.gz']/repo:size/text()"/>
</xsl:stylesheet>
"""


def test_compareAbiVersion():
    assert _compare_abi_version('a', 'a') == 0
    assert _compare_abi_version('a', 'b') is None
    assert _compare_abi_version('a(1)', 'a') == 1
    assert _compare_abi_version('a', 'a(1)') == -1
    assert _compare_abi_version('a(1)', 'a(1)') == 0
    assert _compare_abi_version('libc.so.6(GLIBC_2.3.4)(64 bit)', 'libc.so.6(GLIBC_2.3.4)(64 bit)') == 0
    assert _compare_abi_version('libc.so.6(GLIBC_2.3.4)(64 bit)', 'libc.so.6(GLIBC_2.2.4)(64 bit)') == 1
    assert _compare_abi_version('libc.so.6(GLIBC_2.1.4)(64 bit)', 'libc.so.6(GLIBC_2.2.4)(64 bit)') == -1
    assert _compare_abi_version('libc.so.6(GLIBC_2.1.4)(64 bit)', 'libc.so.6()(64 bit)') == 1

@pytest.mark.download(
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/s/sudo-1.9.17-5.p1.fc43.x86_64.rpm"
)
def test_one(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = RpmRepo()
    package = repo.add_package(binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm')
    assert package.name == 'sudo'
    assert package.arch == 'x86_64'
    assert package.version_str == '1.9.17-5.p1.fc43'
    assert package.version_key == RpmVersion(('0', '1.9.17', '5.p1.fc43'))
    repo.export(output_path, pgp_signer, now=fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm', binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm')
    compare_xml_files(output_path / 'repodata/repomd.xml', expected_path / 'repomd.xml', REPOMD_NORMALIZE, should_populate)
    compare_files(output_path / 'repodata/primary.xml', expected_path / 'primary.xml', should_populate)
    compare_files(output_path / 'repodata/filelists.xml', expected_path / 'filelists.xml', should_populate)
    compare_files(output_path / 'repodata/other.xml', expected_path / 'other.xml', should_populate)

@pytest.mark.download(
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/s/sudo-1.9.17-5.p1.fc43.x86_64.rpm",
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/d/dhcp-devel-4.4.3-22.fc43.x86_64.rpm"
)
def test_two(binaries_path, output_path, expected_path, pgp_signer, fixed_datetime, should_populate):
    repo = RpmRepo()
    repo.add_package(binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm')
    package = repo.add_package(binaries_path / 'dhcp-devel-4.4.3-22.fc43.x86_64.rpm')
    assert package.name == 'dhcp-devel'
    assert package.arch == 'x86_64'
    assert package.version_str == '12:4.4.3-22.fc43'
    assert package.version_key == RpmVersion(('12', '4.4.3', '22.fc43'))
    repo.export(output_path, pgp_signer, now=fixed_datetime, keep_expanded=True)
    compare_files(output_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm', binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm')
    compare_files(output_path / 'dhcp-devel-4.4.3-22.fc43.x86_64.rpm', binaries_path / 'dhcp-devel-4.4.3-22.fc43.x86_64.rpm')
    compare_xml_files(output_path / 'repodata/repomd.xml', expected_path / 'repomd.xml', REPOMD_NORMALIZE, should_populate)
    compare_files(output_path / 'repodata/primary.xml', expected_path / 'primary.xml', should_populate)
    compare_files(output_path / 'repodata/filelists.xml', expected_path / 'filelists.xml', should_populate)
    compare_files(output_path / 'repodata/other.xml', expected_path / 'other.xml', should_populate)

@pytest.mark.download(
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/s/sudo-1.9.17-5.p1.fc43.x86_64.rpm",
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/d/dhcp-devel-4.4.3-22.fc43.x86_64.rpm",
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/m/makepasswd-0.5.3-35.fc43.x86_64.rpm"
)
def test_crud(binaries_path):
    repo = RpmRepo()
    
    package = repo.add_package(binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm')
    repo.del_package(package)
    assert [x for x in repo.packages] == []
    repo.del_package(package) # should succeed
    package1 = repo.add_package(binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm')
    package2 = repo.add_package(binaries_path / 'dhcp-devel-4.4.3-22.fc43.x86_64.rpm')
    repo.del_package(package1)
    assert [x for x in repo.packages] == [package2]

    package1 = repo.add_package(binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm')
    package3 = repo.add_package(binaries_path / 'makepasswd-0.5.3-35.fc43.x86_64.rpm')
    
    repo.del_package(package3)
    assert [x for x in repo.packages] == [package2, package1]
    
    repo.del_package(package2)
    assert [x for x in repo.packages] == [package1]

@pytest.mark.download(
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/s/sudo-1.9.17-5.p1.fc43.x86_64.rpm",
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/d/dhcp-devel-4.4.3-22.fc43.x86_64.rpm",
    "https://rpmfind.net/linux/fedora/linux/releases/43/Everything/x86_64/os/Packages/m/makepasswd-0.5.3-35.fc43.x86_64.rpm"
)
def test_cmd(binaries_path, output_path, pgp_cmd):
    subprocess.run([sys.executable, '-m', 'repopulator', 'rpm'] + 
                   pgp_cmd + [
                    '-p', 
                    binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm', 
                    binaries_path / 'dhcp-devel-4.4.3-22.fc43.x86_64.rpm',
                    binaries_path / 'makepasswd-0.5.3-35.fc43.x86_64.rpm',
                    '-o', output_path
                    ], check=True)
    compare_files(output_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm', binaries_path / 'sudo-1.9.17-5.p1.fc43.x86_64.rpm')
    compare_files(output_path / 'dhcp-devel-4.4.3-22.fc43.x86_64.rpm', binaries_path / 'dhcp-devel-4.4.3-22.fc43.x86_64.rpm')
    compare_files(output_path / 'makepasswd-0.5.3-35.fc43.x86_64.rpm', binaries_path / 'makepasswd-0.5.3-35.fc43.x86_64.rpm')
