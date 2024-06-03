# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""Generating Pacman repositories"""

from __future__ import annotations

import hashlib
import shutil
import stat
import tarfile
import gzip
import zstandard

from pathlib import Path
from datetime import datetime, timezone

from .pgp_signer import PgpSigner
from .util import NoPublicConstructor, VersionKey, file_digest, lowerBound

from typing import IO, Any, BinaryIO, KeysView, Mapping, Optional, Sequence

class PacmanPackage(metaclass=NoPublicConstructor):
    @classmethod
    def _load(cls, srcPath: Path, repoFilename: str) -> PacmanPackage:
        sigPath = srcPath.parent / (srcPath.name + '.sig')
        if not sigPath.exists():
            sigPath = None
        
        st = srcPath.stat()
        with open(srcPath, mode='rb') as pkg:
            digest = file_digest(pkg, hashlib.sha256).hexdigest()
            pkg.seek(0, 0)
            decomp = zstandard.ZstdDecompressor()
            info = None
            files = []
            with decomp.stream_reader(pkg) as tarstream:
                with tarfile.open(mode="r|", fileobj=tarstream) as tar:
                    for member in tar:
                        if member.name == '.PKGINFO':
                            pkginfo = tar.extractfile(member)
                            assert pkginfo is not None
                            info = PacmanPackage.__read_pkginfo(pkginfo)
                        elif not member.name.startswith('.'):
                            if member.isdir() and not member.name.endswith('/'):
                                files.append(member.name + '/')
                            else:
                                files.append(member.name)

            if info is None:
                raise Exception(f'{srcPath} is not a valid Pacman package: no .PKGINFO file')

        desc = {
            'FILENAME': repoFilename,
            'NAME': info['pkgname'],
            'BASE': info['pkgbase'],
            'VERSION': info['pkgver'],
            'DESC': info['pkgdesc'],
            'CSIZE': str(st.st_size),
            'ISIZE': info['size'],
            'SHA256SUM': digest,
            'URL': info['url'],
            'LICENSE': info['license'],
            'ARCH': info['arch'],
            'BUILDDATE': info['builddate'],
            'PACKAGER': info['packager']
        }
        if (replaces := info.get('replace')) is not None:
            desc['REPLACES'] = replaces
        if (conflicts := info.get('conflict')) is not None:
            desc['CONFLICTS'] = conflicts
        if (provides := info.get('provide')) is not None:
            desc['PROVIDES'] = provides
        if (depends := info.get('depend')) is not None:
            desc['DEPENDS'] = depends
        if (optdepends := info.get('optdepend')) is not None:
            desc['OPTDEPENDS'] = optdepends
        if (makedepends := info.get('makedepend')) is not None:
            desc['MAKEDEPENDS'] = makedepends
        if (checkdepend := info.get('checkdepend')) is not None:
            desc['CHECKDEPENDS'] = checkdepend
        

        return cls._create(srcPath, sigPath, desc, files)
    
    def __init__(self, srcPath: Path, sigPath: Optional[Path], desc: dict[str, Any], files: list[str]):
        """Internal do not use.
        Use PacmanRepo.addPackage to create instances of this class
        """
        self.__srcPath = srcPath
        self.__sigPath = sigPath
        self.__desc = desc
        self.__files = files
        self.__versionKey = VersionKey.parse(self.__desc['VERSION'])

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__desc['NAME']
    
    @property 
    def versionStr(self) -> str:
        return self.__desc['VERSION']
    
    @property
    def versionKey(self) -> VersionKey:
        return self.__versionKey
    
    @property
    def arch(self) -> str:
        return self.__desc['ARCH']
    
    @property
    def fields(self) -> Mapping[str, Any]:
        return self.__desc
    
    @property
    def repoFilename(self) -> str:
        return self.__desc['FILENAME']
    
    @property
    def srcPath(self) -> Path:
        return self.__srcPath
    
    @property
    def sigPath(self) -> Optional[Path]:
        return self.__sigPath
    

    def _exportDesc(self, fp: BinaryIO):
        for key, value in self.__desc.items():
            fp.write(f'%{key}%\n'.encode())
            if isinstance(value, str):
                values = (value, )
            else: 
                values = value
            for val in values:
                fp.write(f'{val}\n'.encode())
            fp.write(b'\n')

    def _exportFiles(self, fp: BinaryIO):
        fp.write(b'%FILES%\n')
        for file in self.__files:
            fp.write(file.encode())
            fp.write(b'\n')


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





class PacmanRepo:
    def __init__(self, name: str):
        self.__name = name
        self.__packages: dict[str, list[PacmanPackage]] = {}

    def addPackage(self, path: Path) -> PacmanPackage:
        package = PacmanPackage._load(path, path.name)
        archPackages = self.__packages.setdefault(package.arch, [])
        for idx, existing in enumerate(archPackages):
            if existing.repoFilename == package.repoFilename:
                raise ValueError("duplicate package filename")
        idx = lowerBound(archPackages, package, lambda x, y: x.name < y.name) 
        if idx < len(archPackages) and (existing := archPackages[idx]).name == package.name:
            if existing.versionKey == package.versionKey:
                raise ValueError('Duplicate package')
            if existing.versionKey < package.versionKey:
                archPackages[idx] = package
        else:
            archPackages.insert(idx, package)
        return package
    
    @property
    def name(self):
        return self.__name
    
    @property
    def architectures(self) -> KeysView[str]:
        return self.__packages.keys() 
    
    def packages(self, arch: str) -> Sequence[PacmanPackage]:
        return self.__packages[arch]
    
    def export(self, root: Path, signer: PgpSigner, now: Optional[datetime] = None, keepExpanded=False):
        if now is None:
            now = datetime.now(timezone.utc)

        expanded = root / 'expanded'
        if expanded.exists():
            shutil.rmtree(expanded)
        expanded.mkdir(parents=True)

        dbPart = f'{self.__name}.db'
        filesPart = f'{self.__name}.files'
        
        for arch, archPackages in self.__packages.items():
            expandedArchDir = expanded / arch
            expandedDbDir = expandedArchDir / dbPart
            expandedDbDir.mkdir(parents=True)
            expandedFilesDir = expandedArchDir / filesPart
            expandedFilesDir.mkdir(parents=True)

            for package in archPackages:
                packageDir = expandedDbDir / f'{package.name}-{package.versionStr}'
                packageDir.mkdir(parents=True)
                with open(packageDir / 'desc', 'wb') as descFile:
                    package._exportDesc(descFile)
                
                packageFilesDir = expandedFilesDir / f'{package.name}-{package.versionStr}'
                packageFilesDir.mkdir(parents=True)
                shutil.copy2(packageDir / 'desc', packageFilesDir / 'desc')
                with open(packageFilesDir / 'files', 'wb') as filesFile:
                    package._exportFiles(filesFile)

            archDir = root / arch
            archDir.mkdir(parents=True, exist_ok=True)

            
            self.__collectArchive(expandedDbDir, archDir, signer, now,
                                  dbPart, archPackages, ['desc'])
            
            self.__collectArchive(expandedFilesDir, archDir, signer, now,
                                  filesPart, archPackages, ['desc', 'files'])
            
            
            self.__copyFiles(archDir, signer, archPackages)
            
        
        if not keepExpanded:
            shutil.rmtree(expanded)

    @staticmethod
    def __collectArchive(srcDir: Path, destDir: Path, signer: PgpSigner, now: datetime,
                         stem: str, packages: Sequence[PacmanPackage], filenames: Sequence[str]):
        def norm(info: tarfile.TarInfo):
            info.uid = 0
            info.gid = 0
            info.uname = 'root'
            info.gname = 'wheel'
            info.mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            info.mtime = int(now.timestamp())
            return info
        
        tarpath = destDir / (stem + '.tar.gz')
        with open(tarpath, 'wb') as f_out:
            with gzip.GzipFile(filename=tarpath.name, mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                pythonTypingIsDumb: Any = f_zip
                with tarfile.open(mode="w:", fileobj=pythonTypingIsDumb) as archive:
                    for package in packages:
                        packageDir = Path(f'{package.name}-{package.versionStr}')
                        for filename in filenames:
                            archive.add(srcDir / packageDir / filename, arcname=(packageDir / filename).as_posix(), filter=norm)
        PacmanRepo.__removeExisting(destDir / stem)
        (destDir / stem).symlink_to(tarpath.name)

        tarsigpath = tarpath.parent / (tarpath.name + '.sig')
        PacmanRepo.__removeExisting(tarsigpath)
        signer.binarySignExternal(tarpath, tarsigpath)
        PacmanRepo.__removeExisting(destDir / (stem + '.sig'))
        (destDir / (stem + '.sig')).symlink_to(tarsigpath.name)

    @staticmethod
    def __copyFiles(destDir: Path, signer: PgpSigner, packages: Sequence[PacmanPackage]):

        for existingFile in destDir.glob('*.pkg.tar.zst'):
            existingFile.unlink()

        for package in packages:
            destPath = destDir / package.repoFilename
            destSigPath = destDir / (package.repoFilename + '.sig')

            shutil.copy2(package.srcPath, destPath)
            if (sigPath := package.sigPath) is not None:
                shutil.copy2(sigPath, destSigPath)
            else:
                signer.binarySignExternal(destPath, destSigPath)

    @staticmethod
    def __removeExisting(path: Path):
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()




