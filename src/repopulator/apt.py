# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""Generating APT repositories"""

from __future__ import annotations

import os
import shutil
import gzip
import hashlib
import arpy
import tarfile

from functools import total_ordering
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import AbstractSet, Any, BinaryIO, Dict, KeysView, Mapping, Optional, Sequence, Union

from .pgp_signer import PgpSigner
from .util import NoPublicConstructor, VersionKey, lowerBound, file_digest


class AptPackage(metaclass=NoPublicConstructor):
    @classmethod
    def _load(cls, srcPath: Path, repoFilename: str) -> AptPackage:
        fields: Dict[str, str | list[str]] = {}
        with arpy.Archive(str(srcPath)) as ar:
            it = ar.__iter__()
            firstFile = next(it)
            if firstFile.header.name != b'debian-binary':
                raise Exception(f'{srcPath} is not a valid Debian archive: debian-binary missing')
            secondFile = next(it)
            if not secondFile.header.name.startswith(b'control.'): # type: ignore
                raise Exception(f'{srcPath} is not a valid Debian archive: no control archive')
            with tarfile.open(name=secondFile.header.name, fileobj=secondFile, mode="r") as controlArchive: # type: ignore
                controlFile = None
                try:
                    controlFile = controlArchive.extractfile('./control')
                except KeyError:
                    pass
                if controlFile is None:
                    raise Exception(f'{srcPath} is not a valid Debian archive: no control file')
                lastKey = None
                for line in controlFile: # type: ignore
                    line = line.decode().rstrip()
                    if len(line) == 0:
                        break
                    if lastKey is not None and (line.startswith(' ') or line.startswith('\t')):
                        lastVal = fields[lastKey]
                        if isinstance(lastVal, list):
                            lastVal.append(line[1:])
                        else:
                            fields[lastKey] = [lastVal, line[1:]]
                    else:
                        sepIdx = line.find(':')
                        if sepIdx < 1:
                            raise Exception(f'{srcPath} is not a valid Debian archive: line `{line}` in control file is invalid')
                        key = line[0:sepIdx]
                        value = line[sepIdx + 1:].strip()
                        fields[key] = value
                        lastKey = key
                if (name := fields.get('Package')) is None:
                    raise Exception(f'{srcPath} is not a valid Debian archive: Package field is missing')
                if not isinstance(name, str):
                    raise Exception(f'{srcPath} is not a valid Debian archive: Package field has invalid value')

                if (arch := fields.get('Architecture')) is None:
                    raise Exception(f'{srcPath} is not a valid Debian archive: Architecture field is missing')
                if not isinstance(arch, str):
                    raise Exception(f'{srcPath} is not a valid Debian archive: Architecture field has invalid value')

                if (ver := fields.get('Version')) is None:
                    raise Exception(f'{srcPath} is not a valid Debian archive: Version field is missing')
                if not isinstance(ver, str):
                    raise Exception(f'{srcPath} is not a valid Debian archive: Version field has invalid value')
            
            
            fields['Filename'] = repoFilename
            fields['Size'] = str(srcPath.stat().st_size)
            hashes = [
                (hashlib.md5, 'MD5sum'),
                (hashlib.sha1, 'SHA1'),
                (hashlib.sha256, 'SHA256'),
                (hashlib.sha512, 'SHA512'),
            ]
            for hashFunc, name in hashes:
                with open(srcPath, "rb") as packFile:
                    digest = file_digest(packFile, hashFunc)
                fields[name] = digest.hexdigest()

        return cls._create(srcPath, fields)
    
    def __init__(self, srcPath: Path, fields: Dict[str, str | list[str]]):
        """Internal, do not use
        Use AptRepo.addPackage to create instances of this class
        """
        self.__srcPath = srcPath
        self.__fields = fields
        self.__versionKey = VersionKey.parse(fields['Version']) # type: ignore
        

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__fields['Package']  # type: ignore
    
    @property
    def versionStr(self) -> str:
        return self.__fields['Version']  # type: ignore
    
    @property
    def versionKey(self) -> VersionKey:
        return self.__versionKey
    
    @property
    def arch(self) -> str:
        return self.__fields['Architecture']  # type: ignore
    
    @property
    def fields(self) -> Mapping[str, Any]:
        return self.__fields
    
    @property
    def repoFilename(self) -> str:
        return self.__fields['Filename'] # type: ignore
    
    @property
    def srcPath(self) -> Path:
        return self.__srcPath



    def _writeIndexEntry(self, f: BinaryIO):
        for key, value in self.__fields.items():
            if isinstance(value, str):
                f.write(f'{key}: {value}\n'.encode())
            else:
                f.write(f'{key}: {value[0]}\n'.encode())
                for i in range(1, len(value)):
                    f.write(f' {value[i]}\n'.encode())


@total_ordering
class AptDistribution:
    def __init__(self, 
                 path: Union[PurePosixPath, str],
                 *,
                 origin: str, 
                 label: str,
                 suite: str, 
                 version: str,
                 description: str) -> None:
        path = path if isinstance(path, PurePosixPath) else PurePosixPath(path)
        if path.is_absolute():
            raise ValueError('path value must be a relative path')
        self.path = path

        self.origin = origin
        self.label = label
        self.suite = suite
        self.version = version
        self.description = description

        self.__packages: Dict[str, Dict[str, list[AptPackage]]] = {}

    def __hash__(self):
        return hash(self.path)
    
    def __eq__(self, other: object):
        if isinstance(other, AptDistribution):
            return self.path == other.path
        return NotImplemented
    
    def __lt__(self, other):
        return self.path < other.path
    
    @property
    def components(self) -> KeysView[str]:
        return self.__packages.keys() 
    
    def architectures(self, component: str) -> KeysView[str]:
        return self.__packages[component].keys() 
    
    def packages(self, component: str, arch: str) -> Sequence[AptPackage]:
        return self.__packages[component][arch]

    def addPackage(self, component: str, package: AptPackage):
        arch = package.arch
        archs = self.__packages.setdefault(component, {})
        packages = archs.setdefault(arch, [])
        def packageKey(p: AptPackage): return (p.name, p.versionStr) #apt tools seem to sort by string
        idx = lowerBound(packages, package, lambda x, y: packageKey(x) < packageKey(y)) 
        if idx < len(packages) and packageKey(packages[idx]) == packageKey(package):
            raise ValueError('Duplicate package')
        packages.insert(idx, package)

    def _export(self, root: Path, signer: PgpSigner, now: Optional[datetime] = None):
        if now is None:
            now = datetime.now(timezone.utc)
        
        distDir = root / self.path
        if distDir.exists():
            shutil.rmtree(distDir)
        distDir.mkdir(parents=True)

        components = []
        archs = []
        for comp, compArchs in self.__packages.items():
            components.append(comp)
            for arch in compArchs:
                archs.append(arch)
        components.sort()
        archs.sort()

        packageIndices: Sequence[Path] = []
        for comp in components:
            for arch in archs:
                pack, pack_gz = self.__exportPackages(distDir, comp, arch, now)
                packageIndices += [pack, pack_gz]

        Release_path = distDir / 'Release'
        with open(Release_path, "wb") as f:
            f.write(f'Origin: {self.origin}\n'.encode())
            f.write(f'Label: {self.label}\n'.encode())
            f.write(f'Suite: {self.suite}\n'.encode())
            f.write(f'Codename: {self.path.name}\n'.encode())
            f.write(f'Version: {self.version}\n'.encode())
            f.write(f'Architectures: {",".join(archs)}\n'.encode())
            f.write(f'Components: {",".join(components)}\n'.encode())
            f.write(f'Description: {self.description}\n'.encode())
            f.write(f'Date: {now.strftime("%a, %d %b %Y %I:%M:%S %z")}\n'.encode())

            hashes = [
                (hashlib.md5, 'MD5Sum'),
                (hashlib.sha1, 'SHA1'),
                (hashlib.sha256, 'SHA256'),
                (hashlib.sha512, 'SHA512'),
            ]
            for hashFunc, name in hashes:
                f.write(f'{name}:\n'.encode())
                for packageIndex in packageIndices:
                    with open(packageIndex, "rb") as packFile:
                        digest = file_digest(packFile, hashFunc)
                    f.write(f' {digest.hexdigest()} {packageIndex.stat().st_size: >16} {packageIndex.relative_to(distDir).as_posix()}\n'.encode())
        
        os.utime(Release_path, (now.timestamp(), now.timestamp()))

        InRelease_path = distDir / 'InRelease'
        signer.signInline(Release_path, InRelease_path)
        os.utime(InRelease_path, (now.timestamp(), now.timestamp()))
        Release_pgp_path = Release_path.with_suffix('.pgp')
        signer.signExternal(Release_path, Release_pgp_path)
        os.utime(Release_pgp_path, (now.timestamp(), now.timestamp()))
        
            
            
    def __exportPackages(self, distRoot: Path, component: str, arch: str, now: datetime):
        packagesDir = distRoot / component / f'binary-{arch}'
        if packagesDir.exists():
            shutil.rmtree(packagesDir)
        packagesDir.mkdir(parents=True)

        Packages_path = packagesDir / 'Packages'
        with open(Packages_path, "wb") as f:
            packages = self.__packages.get(component, {}).get(arch, [])
            if len(packages) > 0:
                packages[0]._writeIndexEntry(f)
            for package in packages[1:]:
                f.write(b'\n')
                package._writeIndexEntry(f)
        os.utime(Packages_path, (now.timestamp(), now.timestamp()))

        Packages_gz_path = Packages_path.with_suffix('.gz')
        with open(Packages_path, 'rb') as f_in:
            with open(Packages_gz_path, 'wb') as f_out:
                with gzip.GzipFile(filename=Packages_path.name, mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                    shutil.copyfileobj(f_in, f_zip)
        os.utime(Packages_gz_path, (now.timestamp(), now.timestamp()))

        return (Packages_path, Packages_gz_path)

class AptRepo:
    def __init__(self):
        self.__distributions: set[AptDistribution] = set()
        self.__packages: list[AptPackage] = []

    def addDistribution(self,
                        path: Union[PurePosixPath, str],
                        *,
                        origin: str, 
                        label: str,
                        suite: str, 
                        version: str,
                        description: str) -> AptDistribution:
        dist = AptDistribution(path, origin=origin, label=label, suite=suite, version=version, description=description)
        if dist in self.__distributions:
            raise ValueError('Duplicate distribution')
        self.__distributions.add(dist)
        return dist

    def addPackage(self, path: Path) -> AptPackage:
        package = AptPackage._load(path, path.name)
        for existing in self.__packages:
            if existing.repoFilename == package.repoFilename:
                raise ValueError("duplicate package name")
        self.__packages.append(package)
        return package
    

    @property
    def distributions(self) -> AbstractSet[AptDistribution]:
        return self.__distributions
    
    @property
    def packages(self) -> Sequence[AptPackage]:
        return self.__packages
    
    def export(self, root: Path, signer: PgpSigner, now: Optional[datetime] = None):
        if now is None:
            now = datetime.now(timezone.utc)
        
        
        dists = root / 'dists'
        if dists.exists():
            shutil.rmtree(dists)
        dists.mkdir(parents=True)
        for dist in self.__distributions:
            dist._export(dists, signer, now)

        pool = root / 'pool'
        if pool.exists():
            shutil.rmtree(pool)
        pool.mkdir(parents=True)
        for package in self.__packages:
            dest = pool / package.repoFilename
            shutil.copy2(package.srcPath, dest)
        
