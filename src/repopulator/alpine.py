# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""Generating Alpine apk repositories"""

from __future__ import annotations

import base64
import hashlib
import stat
import tarfile
import zlib
import shutil
import gzip

from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO
from os import PathLike

from repopulator.pki_signer import PkiSigner

from .util import NoPublicConstructor, PackageParsingException, VersionKey, ensure_one_line_str, lower_bound, path_from_pathlike

from typing import IO, Any, KeysView, Mapping, Optional, Sequence


class AlpinePackage(metaclass=NoPublicConstructor):
    """A package in AlpineRepo"""

    @classmethod
    def _load(cls, src_path: Path, force_arch: Optional[str]) -> AlpinePackage:
        st = src_path.stat()
        with open(src_path, 'rb') as apk:
            buf = bytearray(4096)

            # skip signature segment
            decomp = zlib.decompressobj(31)
            while True:
                count = apk.readinto(buf)
                if count == 0:
                    raise PackageParsingException(f'{src_path} is not a valid apk package: no control segment')
                decomp.decompress(memoryview(buf)[:count])
                if len(decomp.unused_data):
                    apk.seek(-len(decomp.unused_data), 1)
                    break
                    
            # control segment is small
            # rather than muck around with adapter file objects let's just extract it
            # into a byte array and read the tar from there
            control_tar = b''
            decomp = zlib.decompressobj(31)
            digester = hashlib.sha1()
            while True:
                count = apk.readinto(buf)
                if count == 0:
                    break
                control_tar += decomp.decompress(memoryview(buf)[:count])
                if len(decomp.unused_data):
                    used_len = count - len(decomp.unused_data)
                    digester.update(memoryview(buf)[:used_len])
                    break
                
                digester.update(memoryview(buf)[:count])
            

            digest = base64.encodebytes(digester.digest()).decode().rstrip()
            with tarfile.open(fileobj=BytesIO(control_tar), mode="r:") as control:
                pkginfo = None
                try:
                    pkginfo = control.extractfile('.PKGINFO')
                except KeyError:
                    pass
                if pkginfo is None:
                    raise PackageParsingException(f'{src_path} is not a valid apk package: no .PKGINFO file')
                info = AlpinePackage.__read_pkginfo(pkginfo)

        index = {
            'C': 'Q1' + digest,
            'P': info['pkgname'],
            'V': info['pkgver'],
            'A': info['arch'] if force_arch is None else force_arch,
            'S': str(st.st_size),
            'I': info['size'],
            'T': info['pkgdesc'],
            'U': info['url'],
            'L': info['license']
        }
        if (origin := info.get('origin')) is not None:
            index['o'] = origin
        if (maintainer := info.get('maintainer')) is not None:
            index['m'] = maintainer
        if (builddate := info.get('builddate')) is not None:
            index['t'] = builddate
        if (commit := info.get('commit')) is not None:
            index['c'] = commit
        if (provider_priority := info.get('provider_priority')) is not None:
            index['k'] = provider_priority
        if (depends := info.get('depend')) is not None:
            index['D'] = ' '.join(depends) if isinstance(depends, list) else depends
        if (provides := info.get('provides')) is not None:
            index['p'] = ' '.join(provides) if isinstance(provides, list) else provides
        if (install_if := info.get('install_if')) is not None:
            index['i'] = ' '.join(install_if) if isinstance(install_if, list) else install_if
            
        return cls._create(src_path, index)
    
    def __init__(self, src_path: Path, index: dict[str, str]):
        """Internal do not use.
        Use AlpineRepo.add_package to create instances of this class
        """
        self.__src_path = src_path
        self.__index = index
        self.__version_key = VersionKey.parse(self.__index['V'])

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__index['P']
    
    @property 
    def version_str(self) -> str:
        """Version of the package as a string"""
        return self.__index['V']
    
    @property
    def version_key(self) -> VersionKey:
        """Version of the package as a properly comparable key"""
        return self.__version_key
    
    @property
    def arch(self) -> str:
        """Architecture of the package"""
        return self.__index['A']
    
    @property
    def fields(self) -> Mapping[str, str]:
        """Information about package stored in the repository index

        The available fields are documented at: https://wiki.alpinelinux.org/wiki/Apk_spec#APKINDEX_Format
        """
        return self.__index
    
    @property
    def repo_filename(self) -> str:
        """Filename of the package when stored inside the repository"""
        return f'{self.name}-{self.version_str}.apk'
    
    @property
    def src_path(self) -> Path:
        """Path to the original package file"""
        return self.__src_path
    
    def _export_index(self, f: IO[bytes]):
        for key, value in self.__index.items():
            f.write(f'{key}:{value}\n'.encode())
        f.write(b'\n')

    @staticmethod
    def __read_pkginfo(fp: IO[bytes]):
        headers: dict[str, str | list[str]] = {}

        for line in fp:
            line = line.decode()
            if len(line) == 0:
                break
            if line.startswith('#'):
                continue
            eqpos = line.find('=')
            if eqpos == -1:
                continue
            key = line[:eqpos].strip()
            value = line[eqpos+1:].strip()
            existing = headers.get(key)
            if existing is not None:
                if isinstance(existing, str):
                    value = [existing, value]
                else:
                    existing.append(value)
                    value = existing
            headers[key] = value
        return headers


class AlpineRepo:
    """Generates Alpine apk repositories"""

    def __init__(self, desc: str):
        """Constructor for AlpineRepo class

        Args:
            desc: repository description. This is the description shown
                when performing `apk update`
        """

        self.__desc = ensure_one_line_str(desc, 'desc')
        self.__packages: dict[str, list[AlpinePackage]] = {}

    def add_package(self, path: str | PathLike[str], force_arch: Optional[str] = None) -> AlpinePackage:
        """Adds a package to the repository
        
        Args:
            path: the path to `.apk` file for the package.
            force_arch: the architecture (e.g. "x86_64", "aarch64", etc.) to use if the package
                that are marked "noarch". All Alpine packages in a repo must belong to some architecture.

        Returns:
            an AlpinePackage object for the added package
        """

        path = path_from_pathlike(path)
        package = AlpinePackage._load(path, force_arch)
        if package.arch == 'noarch':
            raise ValueError('package has "noarch" architecture, you must use force_arch parameter to specify which repo architecture to assign it to')
        arch_packages = self.__packages.setdefault(package.arch, [])
        idx = lower_bound(arch_packages, package, lambda x, y: self._package_key(x) < self._package_key(y))
        if idx < len(arch_packages) and self._package_key(arch_packages[idx]) == self._package_key(package):
            raise ValueError(f'Duplicate package {path}, existing: {arch_packages[idx].src_path}')
        arch_packages.insert(idx, package)
        return package
    
    def del_package(self, package: AlpinePackage):
        """Removes a package from this repository

        It is not an error to pass a package that is not in a repository to this function.
        It will be ignored in such case.

        Args:
            package: the package to remove
        """
        archs_to_delete = []
        for arch, arch_packages in self.__packages.items():
            idx = lower_bound(arch_packages, package, lambda x, y: self._package_key(x) < self._package_key(y))
            if idx < len(arch_packages) and arch_packages[idx] is package:
                del arch_packages[idx]
                if not arch_packages:
                    archs_to_delete.append(arch)
        for arch in archs_to_delete:
            del self.__packages[arch]
        

    @staticmethod
    def _package_key(package: AlpinePackage): 
        return (package.name, package.version_key)
    
    @property 
    def description(self):
        """Repository description"""
        return self.__desc
    
    @property
    def architectures(self) -> KeysView[str]:
        """Architectures in this repository"""
        return self.__packages.keys() 
    
    def packages(self, arch: str) -> Sequence[AlpinePackage]:
        """Packages for a given architecture"""
        return self.__packages[arch]
    
    def export(self, root: str | PathLike[str], signer: PkiSigner, signer_name: str,
               now: Optional[datetime] = None, keep_expanded: bool = False):
        """Export the repository into a given folder
        
        This actually creates an on-disk repository suitable to serve to `apk` clients. If the directory to export to
        already exists the export process tries to handle pre-existing content there gracefully. Content that doesn't
        conflict with repository content will be left alone. Content that does conflict will be removed or overwritten.

        Specifically any existing <arch>/*.apk files will be removed and replaced with the ones from the repository for
        the architectures in the repository. 

        Args:
            root: the root path to export to. The directory will be created if it does not exist
            signer: A PkiSigner instance to use for signing the repository. Note that this is used to only sign the
                repository itself, not the packages in it. The packages need to be signed ahead of time which usually
                happens automatically if you use `abuild` tool
            signer_name: The "name" of the signer to use. It is usually something like "mymail@mydomain.com-1234abcd" 
                (see https://wiki.alpinelinux.org/wiki/Abuild_and_Helpers#Setting_up_the_build_environment for details).
                Unlike what `pkg` tool does it is not parsed out of private key filename - you have to pass it here manually.
            now: optional timestamp to use when generating files (including various timestamp fields *inside* files).
                Specifying this argument allows for reproducible repository creation.
            keep_expanded: keep intermediate uncompressed files on disk. This is useful for testing and
                troubleshooting only
        """
        if now is None:
            now = datetime.now(timezone.utc)

        root = path_from_pathlike(root)
        expanded = root / 'expanded'
        if expanded.exists():
            shutil.rmtree(expanded)
        expanded.mkdir(parents=True)

        description = expanded / 'DESCRIPTION'
        description.write_text(self.__desc)

        def norm(info: tarfile.TarInfo):
            info.uid = 0
            info.gid = 0
            info.uname = ''
            info.gname = ''
            info.mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            info.mtime = int(now.timestamp())
            return info

        for arch, arch_packages in self.__packages.items():
            expanded_arch_dir = expanded / arch
            expanded_arch_dir.mkdir()

            apkindex = expanded_arch_dir / 'APKINDEX'
            with open(apkindex, 'wb') as f:
                for package in arch_packages:
                    package._export_index(f)

            
            index_tgz = expanded_arch_dir / 'index.tgz'
            with open(index_tgz, 'wb') as f_out:
                with gzip.GzipFile(filename='', mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                    python_typing_is_dumb: Any = f_zip
                    with tarfile.open(mode="w:", fileobj=python_typing_is_dumb) as archive:
                        archive.add(description, arcname=description.name, filter=norm)
                        archive.add(apkindex, arcname=apkindex.name, filter=norm)

            sig_tgz = expanded_arch_dir / 'sig.tgz'
            self.__create_index_signature(index_tgz, sig_tgz, signer, signer_name, now)
            
            arch_dir = root / arch
            arch_dir.mkdir(parents=True, exist_ok=True)
            with open(arch_dir / 'APKINDEX.tar.gz', 'wb') as dest:
                with open(sig_tgz, 'rb') as f:
                    shutil.copyfileobj(f, dest)
                with open(index_tgz, 'rb') as f:
                    shutil.copyfileobj(f, dest)

            for existing_file in arch_dir.glob('*.apk'):
                existing_file.unlink()
            for package in arch_packages:
                shutil.copy2(package.src_path, arch_dir / package.repo_filename)

        if not keep_expanded:
            shutil.rmtree(expanded)

    @staticmethod
    def __create_index_signature(path: Path, sig_path: Path, signer: PkiSigner, signer_name: str, now: datetime):
        signature = signer.get_alpine_signature(path)
        with open(sig_path, 'wb') as f_out:
            with gzip.GzipFile(filename='', mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                python_typing_is_dumb: Any = f_zip
                with tarfile.open(mode="w:", fileobj=python_typing_is_dumb) as archive:
                    info = tarfile.TarInfo(f'.SIGN.RSA.{signer_name}.rsa.pub')
                    info.uid = 0
                    info.gid = 0
                    info.uname = ''
                    info.gname = ''
                    info.mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
                    info.mtime = int(now.timestamp())
                    info.type = tarfile.REGTYPE
                    info.size = len(signature)
                    archive.addfile(info, BytesIO(signature))
                    # HACK: we need a "cut" archive with no end null blocks. Let's suppress close()
                    #       since **big assumption** it only writes the terminators and does no flushing of 
                    #       unwritten data. See TarFile.close() for details
                    def do_nothing(): pass
                    archive.close = do_nothing

