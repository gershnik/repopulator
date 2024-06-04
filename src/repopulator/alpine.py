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

from repopulator.pki_signer import PkiSigner

from .util import NoPublicConstructor, VersionKey, lowerBound

from typing import IO, Any, KeysView, Mapping, Optional, Sequence


class AlpinePackage(metaclass=NoPublicConstructor):
    @classmethod
    def _load(cls, srcPath: Path, forceArch: Optional[str]) -> AlpinePackage:

        st = srcPath.stat()

        
        with open(srcPath, 'rb') as apk:
            buf = bytearray(4096)

            # skip signature segment
            decomp = zlib.decompressobj(31)
            while True:
                count = apk.readinto(buf)
                if count == 0:
                    raise Exception(f'{srcPath} is not a valid apk package: no control segment')
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
                    usedLen = count - len(decomp.unused_data)
                    digester.update(memoryview(buf)[:usedLen])
                    break
                else:
                    digester.update(memoryview(buf)[:count])
            

            digest = base64.encodebytes(digester.digest()).decode().rstrip()
            with tarfile.open(fileobj=BytesIO(control_tar), mode="r:") as control:
                pkginfo = None
                try:
                    pkginfo = control.extractfile('.PKGINFO')
                except KeyError:
                    pass
                if pkginfo is None:
                    raise Exception(f'{srcPath} is not a valid apk package: no .PKGINFO file')
                info = AlpinePackage.__read_pkginfo(pkginfo)

        index = {
            'C': 'Q1' + digest,
            'P': info['pkgname'],
            'V': info['pkgver'],
            'A': info['arch'] if forceArch is None else forceArch,
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
            
        return cls._create(srcPath, index)
    
    def __init__(self, srcPath: Path, index: dict[str, str]):
        """Internal do not use.
        Use AlpineRepo.addPackage to create instances of this class
        """
        self.__srcPath = srcPath
        self.__index = index
        self.__versionKey = VersionKey.parse(self.__index['V'])

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__index['P']
    
    @property 
    def versionStr(self) -> str:
        return self.__index['V']
    
    @property
    def versionKey(self) -> VersionKey:
        return self.__versionKey
    
    @property
    def arch(self) -> str:
        return self.__index['A']
    
    @property
    def fields(self) -> Mapping[str, str]:
        return self.__index
    
    @property
    def repoFilename(self) -> str:
        return f'{self.name}-{self.versionStr}.apk'
    
    @property
    def srcPath(self) -> Path:
        return self.__srcPath
    
    def _exportIndex(self, f: IO[bytes]):
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
    def __init__(self, desc: str):
        self.__desc = desc
        self.__packages: dict[str, list[AlpinePackage]] = {}

    def addPackage(self, path: Path, forceArch: Optional[str] = None) -> AlpinePackage:
        package = AlpinePackage._load(path, forceArch)
        if package.arch == 'noarch':
            raise Exception('package has "noarch" architecture, you must use forceArch parameter to specify which repo architecture to assign it to')
        archPackages = self.__packages.setdefault(package.arch, [])
        def packageKey(x: AlpinePackage): return (x.name, x.versionKey)
        idx = lowerBound(archPackages, package, lambda x, y: packageKey(x) < packageKey(y))
        if idx < len(archPackages) and packageKey(archPackages[idx]) == packageKey(package):
            raise ValueError(f'Duplicate package {path}, exsiting: {archPackages[idx].srcPath}')
        archPackages.insert(idx, package)
        return package
    
    @property 
    def description(self):
        return self.__desc
    
    @property
    def architectures(self) -> KeysView[str]:
        return self.__packages.keys() 
    
    def packages(self, arch: str) -> Sequence[AlpinePackage]:
        return self.__packages[arch]
    
    def export(self, root: Path, signer: PkiSigner, keyName: str, now: Optional[datetime] = None, keepExpanded=False):
        if now is None:
            now = datetime.now(timezone.utc)

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

        for arch, archPackages in self.__packages.items():
            expandedArchDir = expanded / arch
            expandedArchDir.mkdir()

            apkindex = expandedArchDir / 'APKINDEX'
            with open(apkindex, 'wb') as f:
                for package in archPackages:
                    package._exportIndex(f)

            
            index_tgz = expandedArchDir / 'index.tgz'
            with open(index_tgz, 'wb') as f_out:
                with gzip.GzipFile(filename='', mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                    pythonTypingIsDumb: Any = f_zip
                    with tarfile.open(mode="w:", fileobj=pythonTypingIsDumb) as archive:
                        archive.add(description, arcname=description.name, filter=norm)
                        archive.add(apkindex, arcname=apkindex.name, filter=norm)

            sig_tgz = expandedArchDir / 'sig.tgz'
            self.__createIndexSignature(index_tgz, sig_tgz, signer, keyName, now)
            
            archDir = root / arch
            archDir.mkdir(parents=True, exist_ok=True)
            with open(archDir / 'APKINDEX.tar.gz', 'wb') as dest:
                with open(sig_tgz, 'rb') as f:
                    shutil.copyfileobj(f, dest)
                with open(index_tgz, 'rb') as f:
                    shutil.copyfileobj(f, dest)

            for existingFile in archDir.glob('*.apk'):
                existingFile.unlink()
            for package in archPackages:
                shutil.copy2(package.srcPath, archDir / package.repoFilename)

        if not keepExpanded:
            shutil.rmtree(expanded)

    @staticmethod
    def __createIndexSignature(path: Path, sigPath: Path, signer: PkiSigner, keyName: str, now: datetime):
        signature = signer.getAlpineSignature(path)
        with open(sigPath, 'wb') as f_out:
            with gzip.GzipFile(filename='', mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                pythonTypingIsDumb: Any = f_zip
                with tarfile.open(mode="w:", fileobj=pythonTypingIsDumb) as archive:
                    info = tarfile.TarInfo(f'.SIGN.RSA.{keyName}.rsa.pub')
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
                    def doNothing(): pass
                    archive.close = doNothing



            