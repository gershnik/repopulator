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
from os import PathLike

from .pgp_signer import PgpSigner
from .util import NoPublicConstructor, PackageParsingException, VersionKey, ensure_one_line_str, file_digest, lower_bound, path_from_pathlike

from typing import IO, Any, BinaryIO, KeysView, Mapping, Optional, Sequence

class PacmanPackage(metaclass=NoPublicConstructor):
    """A package in PacmanRepo"""
    @classmethod
    def _load(cls, src_path: Path, repo_filename: str) -> PacmanPackage:
        sig_path = src_path.parent / (src_path.name + '.sig')
        if not sig_path.exists():
            sig_path = None
        
        st = src_path.stat()
        with open(src_path, mode='rb') as pkg:
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
                raise PackageParsingException(f'{src_path} is not a valid Pacman package: no .PKGINFO file')

        desc = {
            'FILENAME': repo_filename,
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
        

        return cls._create(src_path, sig_path, desc, files)
    
    def __init__(self, src_path: Path, sig_path: Optional[Path], desc: dict[str, Any], files: list[str]):
        """Internal do not use.
        Use [add_package][repopulator.PacmanRepo.add_package] to create instances of this class
        """
        self.__src_path = src_path
        self.__sig_path = sig_path
        self.__desc = desc
        self.__files = files
        self.__version_key = VersionKey.parse(self.__desc['VERSION'])

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__desc['NAME']
    
    @property 
    def version_str(self) -> str:
        """Version of the package as a string"""
        return self.__desc['VERSION']
    
    @property
    def version_key(self) -> VersionKey:
        """Version of the package as a properly comparable key"""
        return self.__version_key
    
    @property
    def arch(self) -> str:
        """Architecture of the package"""
        return self.__desc['ARCH']
    
    @property
    def fields(self) -> Mapping[str, Any]:
        """Information about package stored in the repository index

        See https://repod.archlinux.page/repositories/sync_database.html#desc-v2
        for information about available fields
        """
        return self.__desc
    
    @property
    def repo_filename(self) -> str:
        """Filename of the package when stored inside the repository"""
        return self.__desc['FILENAME']
    
    @property
    def src_path(self) -> Path:
        """Path to the original package file"""
        return self.__src_path
    
    @property
    def sig_path(self) -> Optional[Path]:
        """Path to the package signature file, if present"""
        return self.__sig_path
    

    def _export_desc(self, fp: BinaryIO):
        for key, value in self.__desc.items():
            fp.write(f'%{key}%\n'.encode())
            if isinstance(value, str):
                values = (value, )
            else: 
                values = value
            for val in values:
                fp.write(f'{val}\n'.encode())
            fp.write(b'\n')

    def _export_files(self, fp: BinaryIO):
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
    """Generates Pacman repositories"""

    def __init__(self, name: str):
        """Constructor for AlpineRepo class

        Args:
            name: repository name.
        """
        self.__name = ensure_one_line_str(name, 'name')
        self.__packages: dict[str, list[PacmanPackage]] = {}

    def add_package(self, path: str | PathLike[str]) -> PacmanPackage:
        """Adds a package to the repository

        Args:
            path: the path to `.zst` file for the package. If a matching `.zst.sig` file exists alongside it,
                it will be used as a signature file.
        Returns:
            a PacmanPackage object for the added package
        """
        path = path_from_pathlike(path)
        package = PacmanPackage._load(path, path.name)
        arch_packages = self.__packages.setdefault(package.arch, [])
        for idx, existing in enumerate(arch_packages):
            if existing.repo_filename == package.repo_filename:
                raise ValueError("duplicate package filename")
        idx = lower_bound(arch_packages, package, lambda x, y: x.name < y.name)
        if idx < len(arch_packages) and (existing := arch_packages[idx]).name == package.name:
            if existing.version_key == package.version_key:
                raise ValueError('Duplicate package')
            if existing.version_key < package.version_key:
                arch_packages[idx] = package
        else:
            arch_packages.insert(idx, package)
        return package
    
    def del_package(self, package: PacmanPackage):
        """Removes a package from this repository

        It is not an error to pass a package that is not in a repository to this function.
        It will be ignored in such case.

        Args:
            package: the package to remove
        """
        arch_packages = self.__packages.get(package.arch, [])
        idx = lower_bound(arch_packages, package, lambda x, y: x.name < y.name)
        if idx < len(arch_packages) and arch_packages[idx] is package:
            del arch_packages[idx]
            if not arch_packages:
                del self.__packages[package.arch]
    
    @property
    def name(self):
        """Repository name"""
        return self.__name
    
    @property
    def architectures(self) -> KeysView[str]:
        """Architectures in this repository"""
        return self.__packages.keys() 
    
    def packages(self, arch: str) -> Sequence[PacmanPackage]:
        """Packages for a given architecture"""
        return self.__packages[arch]
    
    def export(self, root: Path, signer: PgpSigner, now: Optional[datetime] = None, keep_expanded: bool = False):
        """Export the repository into a given folder

        This actually creates an on-disk repository suitable to serve to `pacman` clients. If the directory to export to
        already exists the export process tries to handle pre-existing content there gracefully. Content that doesn't
        conflict with repository content will be left alone. Content that does conflict will be removed or overwritten.

        Specifically any existing <arch>/.pkg.tar.zst and <arch>/.pkg.tar.zst.sig files will be removed and
        replaced with the ones from the repository for the architectures in the repository.

        Args:
            root: the root path to export to. The directory will be created if it does not exist
            signer: A PgpSigner instance to use for signing the repository. It is used to sign the
                repository itself and any packages that do not have pre-existing signatures.
            now: optional timestamp to use when generating files (including various timestamp fields *inside* files).
                Specifying this argument allows for reproducible repository creation.
            keep_expanded: keep intermediate uncompressed files on disk. This is useful for testing and
                troubleshooting only
        """
        if now is None:
            now = datetime.now(timezone.utc)

        expanded = root / 'expanded'
        if expanded.exists():
            shutil.rmtree(expanded)
        expanded.mkdir(parents=True)

        db_part = f'{self.__name}.db'
        files_part = f'{self.__name}.files'
        
        for arch, arch_packages in self.__packages.items():
            expanded_arch_dir = expanded / arch
            expanded_db_dir = expanded_arch_dir / db_part
            expanded_db_dir.mkdir(parents=True)
            expanded_files_dir = expanded_arch_dir / files_part
            expanded_files_dir.mkdir(parents=True)

            for package in arch_packages:
                package_dir = expanded_db_dir / f'{package.name}-{package.version_str}'
                package_dir.mkdir(parents=True)
                with open(package_dir / 'desc', 'wb') as desc_file:
                    package._export_desc(desc_file)
                
                package_files_dir = expanded_files_dir / f'{package.name}-{package.version_str}'
                package_files_dir.mkdir(parents=True)
                shutil.copy2(package_dir / 'desc', package_files_dir / 'desc')
                with open(package_files_dir / 'files', 'wb') as files_file:
                    package._export_files(files_file)

            arch_dir = root / arch
            arch_dir.mkdir(parents=True, exist_ok=True)

            
            self.__collect_archive(expanded_db_dir, arch_dir, signer, now,
                                   db_part, arch_packages, ['desc'])
            
            self.__collect_archive(expanded_files_dir, arch_dir, signer, now,
                                   files_part, arch_packages, ['desc', 'files'])
            
            
            self.__copy_files(arch_dir, signer, arch_packages)
            
        
        if not keep_expanded:
            shutil.rmtree(expanded)

    @staticmethod
    def __collect_archive(src_dir: Path, dest_dir: Path, signer: PgpSigner, now: datetime,
                          stem: str, packages: Sequence[PacmanPackage], filenames: Sequence[str]):
        def norm(info: tarfile.TarInfo):
            info.uid = 0
            info.gid = 0
            info.uname = 'root'
            info.gname = 'wheel'
            info.mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            info.mtime = int(now.timestamp())
            return info
        
        tarpath = dest_dir / (stem + '.tar.gz')
        with open(tarpath, 'wb') as f_out:
            with gzip.GzipFile(filename=tarpath.name, mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                python_typing_is_dumb: Any = f_zip
                with tarfile.open(mode="w:", fileobj=python_typing_is_dumb) as archive:
                    for package in packages:
                        package_dir = Path(f'{package.name}-{package.version_str}')
                        for filename in filenames:
                            archive.add(src_dir / package_dir / filename, arcname=(package_dir / filename).as_posix(), filter=norm)
        PacmanRepo.__remove_existing(dest_dir / stem)
        (dest_dir / stem).symlink_to(tarpath.name)

        tarsigpath = tarpath.parent / (tarpath.name + '.sig')
        PacmanRepo.__remove_existing(tarsigpath)
        signer.binary_sign_external(tarpath, tarsigpath)
        PacmanRepo.__remove_existing(dest_dir / (stem + '.sig'))
        (dest_dir / (stem + '.sig')).symlink_to(tarsigpath.name)

    @staticmethod
    def __copy_files(dest_dir: Path, signer: PgpSigner, packages: Sequence[PacmanPackage]):

        for existing_file in dest_dir.glob('*.pkg.tar.zst'):
            existing_file.unlink()
        for existing_file in dest_dir.glob('*.pkg.tar.zst.sig'):
            existing_file.unlink()

        for package in packages:
            dest_path = dest_dir / package.repo_filename
            dest_sig_path = dest_dir / (package.repo_filename + '.sig')

            shutil.copy2(package.src_path, dest_path)
            if (sig_path := package.sig_path) is not None:
                shutil.copy2(sig_path, dest_sig_path)
            else:
                signer.binary_sign_external(dest_path, dest_sig_path)

    @staticmethod
    def __remove_existing(path: Path):
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()




