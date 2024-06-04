# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""Generating FreeBSD pkg repositories"""

from __future__ import annotations

import tarfile
import shutil
import stat
import json
import textwrap
import hashlib

from pathlib import Path
from datetime import datetime, timezone

from typing import Any, BinaryIO, Mapping, Optional, Sequence

from .pki_signer import PkiSigner
from .util import NoPublicConstructor, lowerBound, VersionKey, file_digest


class FreeBSDPackage(metaclass=NoPublicConstructor):
    @classmethod
    def _load(cls, srcPath: Path, repoFilename: str) -> FreeBSDPackage:
        st = srcPath.stat()
        with open(srcPath, mode='rb') as pkg:
            digest = file_digest(pkg, hashlib.sha256).hexdigest()
        with tarfile.open(srcPath, mode="r") as pkg:
            manifest = None
            try:
                manifest = pkg.extractfile('+COMPACT_MANIFEST')
            except KeyError:
                pass
            if manifest is None:
                raise Exception(f'{srcPath} is not a valid FreeBSD package: no +COMPACT_MANIFEST file')
            manifestBytes = manifest.readline() # the whole thing should be 1 line
        rawData = json.loads(manifestBytes)
        fields = {
            'name': rawData['name'],
            'origin': rawData['origin'],
            'version': rawData['version'],
            'comment': rawData['comment'],
            'maintainer': rawData['maintainer'],
            'www': rawData['www'],
            'abi': rawData['abi'],
            'arch': rawData['arch'],
            'prefix': rawData['prefix'],
            'sum': digest,
            'flatsize': rawData['flatsize'],
            'path': f'All/{repoFilename}',
            'repopath': f'All/{repoFilename}',
            'pkgsize': st.st_size,
            'desc': rawData['desc'],
            'annotations': rawData['annotations']
        }
        return cls._create(srcPath, manifestBytes, fields)

    def __init__(self, srcPath: Path, manifest: bytes, fields: dict[str, Any]) -> None:
        """Internal do not use.
        Use FreeBSDRepo.addPackage to create instances of this class
        """
        self.__srcPath = srcPath
        self.__manifest = manifest
        self.__fields = fields
        self.__versionKey = VersionKey.parse(self.__fields['version'])

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__fields['name']
    
    @property 
    def versionStr(self) -> str:
        return self.__fields['version']
    
    @property
    def versionKey(self) -> VersionKey:
        return self.__versionKey
    
    @property
    def arch(self) -> str:
        return self.__fields['arch']
    
    @property
    def fields(self) -> Mapping[str, Any]:
        return self.__fields
    
    @property
    def repoFilename(self) -> str:
        return self.__fields['repopath'][4:]
    
    @property
    def srcPath(self) -> Path:
        return self.__srcPath
        

    def _exportToSite(self, fp: BinaryIO):
        fp.write(self.__manifest)
        fp.write(b'\n')

    def _exportToData(self, parent: list):
        parent.append(self.__fields)


class FreeBSDRepo:
    def __init__(self):
        self.__packages: list[FreeBSDPackage] = []

    def addPackage(self, path: Path) -> FreeBSDPackage:
        package = FreeBSDPackage._load(path, path.name)
        for existing in self.__packages:
            if existing.repoFilename == package.repoFilename:
                raise ValueError("duplicate package filename")
        def packageKey(p: FreeBSDPackage): return (p.name, p.versionKey)
        idx = lowerBound(self.__packages, package, lambda x, y: packageKey(x) < packageKey(y)) 
        if idx < len(self.__packages) and packageKey(self.__packages[idx]) == packageKey(package):
            raise ValueError('Duplicate package')
        self.__packages.insert(idx, package)

        return package
    
    @property
    def packages(self) -> Sequence[FreeBSDPackage]:
        return self.__packages

    
    def export(self, root: Path, signer: PkiSigner, now: Optional[datetime] = None, keepExpanded=False):
        if now is None:
            now = datetime.now(timezone.utc)
        
        packagesite = root / 'packagesite'
        if packagesite.exists():
            shutil.rmtree(packagesite)
        packagesite.mkdir(parents=True)
        with open(packagesite / 'packagesite.yaml', "wb") as yaml:
            for package in self.__packages:
                package._exportToSite(yaml)

        self.__archive(packagesite, 'packagesite.yaml', signer, now)
        if not keepExpanded:
            shutil.rmtree(packagesite)

        data = root / 'data'
        if data.exists():
            shutil.rmtree(data)
        data.mkdir(parents=True)
        with open(data / 'data', 'w') as datafile:
            content = {'groups': [], 'packages': []}
            for package in self.__packages:
                package._exportToData(content['packages'])
            json.dump(content, datafile, separators=(',', ':'))

        self.__archive(data, 'data', signer, now)
        if not keepExpanded:
            shutil.rmtree(data)

        metatext = textwrap.dedent(
                '''
                version = 2;
                packing_format = "txz";
                manifests = "packagesite.yaml";
                data = "data";
                filesite = "filesite.yaml";
                manifests_archive = "packagesite";
                filesite_archive = "filesite";
                ''').lstrip().encode()

        (root / 'meta').write_bytes(metatext)
        (root / 'meta.conf').write_bytes(metatext)
        
        allFolder = root / 'All'
        if allFolder.exists():
            shutil.rmtree(allFolder)
        allFolder.mkdir(parents=True)
        for package in self.__packages:
            dest = allFolder / package.repoFilename
            shutil.copy2(package.srcPath, dest)


    @staticmethod
    def __archive(directory: Path, filename: str, signer: PkiSigner, now: datetime):
        signature = signer.getFreeBSDSignature(directory / filename)
        with open(directory / 'signature', 'wb') as sigFile:
            sigFile.write(signature)


        def norm(info: tarfile.TarInfo):
            info.uid = 0
            info.gid = 0
            info.uname = 'root'
            info.gname = 'wheel'
            info.mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            info.mtime = int(now.timestamp())
            return info
        
        txzfile = directory.with_suffix('.txz')
        with tarfile.open(txzfile, "w:xz") as archive:
            archive.add(directory / 'signature', arcname='signature', filter=norm)
            archive.add(directory / filename, arcname=filename, filter=norm)
        shutil.copy2(txzfile, txzfile.with_suffix('.pkg'))

