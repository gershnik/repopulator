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
from os import PathLike

from typing import Any, BinaryIO, Mapping, Optional, Sequence

from .pki_signer import PkiSigner
from .util import NoPublicConstructor, PackageParsingException, lower_bound, VersionKey, file_digest, path_from_pathlike


class FreeBSDPackage(metaclass=NoPublicConstructor):
    """A package in FreeBSDRepo"""

    @classmethod
    def _load(cls, src_path: Path, repo_filename: str) -> FreeBSDPackage:
        st = src_path.stat()
        with open(src_path, mode='rb') as pkg:
            digest = file_digest(pkg, hashlib.sha256).hexdigest()
        with tarfile.open(src_path, mode="r") as pkg:
            manifest = None
            try:
                manifest = pkg.extractfile('+COMPACT_MANIFEST')
            except KeyError:
                pass
            if manifest is None:
                raise PackageParsingException(f'{src_path} is not a valid FreeBSD package: no +COMPACT_MANIFEST file')
            manifest_bytes = manifest.readline() # the whole thing should be 1 line
        raw_data = json.loads(manifest_bytes)
        fields = {
            'name': raw_data['name'],
            'origin': raw_data['origin'],
            'version': raw_data['version'],
            'comment': raw_data['comment'],
            'maintainer': raw_data['maintainer'],
            'www': raw_data['www'],
            'abi': raw_data['abi'],
            'arch': raw_data['arch'],
            'prefix': raw_data['prefix'],
            'sum': digest,
            'flatsize': raw_data['flatsize'],
            'path': f'All/{repo_filename}',
            'repopath': f'All/{repo_filename}',
            'pkgsize': st.st_size,
            'desc': raw_data['desc'],
            'annotations': raw_data['annotations']
        }
        return cls._create(src_path, manifest_bytes, fields)

    def __init__(self, src_path: Path, manifest: bytes, fields: dict[str, Any]) -> None:
        """Internal do not use.
        Use FreeBSDRepo.add_package to create instances of this class
        """
        self.__src_path = src_path
        self.__manifest = manifest
        self.__fields = fields
        self.__version_key = VersionKey.parse(self.__fields['version'])

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__fields['name']
    
    @property 
    def version_str(self) -> str:
        """Version of the package as a string"""
        return self.__fields['version']
    
    @property
    def version_key(self) -> VersionKey:
        """Version of the package as a properly comparable key"""
        return self.__version_key
    
    @property
    def arch(self) -> str:
        """Architecture of the package"""
        return self.__fields['arch']
    
    @property
    def fields(self) -> Mapping[str, Any]:
        """Information about package stored in the repository index."""
        return self.__fields
    
    @property
    def repo_filename(self) -> str:
        """Filename of the package when stored inside the repository"""
        return self.__fields['repopath'][4:]
    
    @property
    def src_path(self) -> Path:
        """Path to the original package file"""
        return self.__src_path
        

    def _export_to_site(self, fp: BinaryIO):
        fp.write(self.__manifest)
        fp.write(b'\n')

    def _export_to_data(self, parent: list):
        parent.append(self.__fields)


class FreeBSDRepo:
    """Generates FreeBSD pkg repositories"""

    def __init__(self):
        """Constructor for FreeBSDRepo class"""
        self.__packages: list[FreeBSDPackage] = []

    def add_package(self, path: str | PathLike[str]) -> FreeBSDPackage:
        """Adds a package to the repository

        Args:
            path: the path to `.pkg` file for the package.
        Returns:
            a FreeBSDPackage object for the added package
        """
        path = path_from_pathlike(path)
        package = FreeBSDPackage._load(path, path.name)
        for existing in self.__packages:
            if existing.repo_filename == package.repo_filename:
                raise ValueError("duplicate package filename")
        idx = lower_bound(self.__packages, package, lambda x, y: self._package_key(x) < self._package_key(y))
        if idx < len(self.__packages) and self._package_key(self.__packages[idx]) == self._package_key(package):
            raise ValueError('Duplicate package')
        self.__packages.insert(idx, package)

        return package
    
    def del_package(self, package: FreeBSDPackage):
        """Removes a package from this repository

        It is not an error to pass a package that is not in a repository to this function.
        It will be ignored in such case.

        Args:
            package: the package to remove
        """
        idx = lower_bound(self.__packages, package, lambda x, y: self._package_key(x) < self._package_key(y))
        if idx < len(self.__packages) and self.__packages[idx] is package:
            del self.__packages[idx]

    @staticmethod
    def _package_key(package: FreeBSDPackage): 
        return (package.name, package.version_key)
    
    @property
    def packages(self) -> Sequence[FreeBSDPackage]:
        """Packages in the repository"""
        return self.__packages

    
    def export(self, root: str | PathLike[str], signer: PkiSigner, now: Optional[datetime] = None, keep_expanded: bool = False):
        """Export the repository into a given folder

        This actually creates an on-disk repository suitable to serve to `pkg` clients. If the directory to export to
        already exists the export process tries to handle pre-existing content there gracefully. Content that doesn't
        conflict with repository content will be left alone. Content that does conflict will be removed or overwritten.

        Specifically any existing All/*.pkg files will be removed and replaced with the ones from the repository.

        Args:
            root: the root path to export to. The directory will be created if it does not exist
            signer: A PkiSigner instance to use for signing the repository.
            now: optional timestamp to use when generating files (including various timestamp fields *inside* files).
                Specifying this argument allows for reproducible repository creation.
            keep_expanded: keep intermediate uncompressed files on disk. This is useful for testing and
                troubleshooting only
        """

        if now is None:
            now = datetime.now(timezone.utc)
        
        root = path_from_pathlike(root)
        packagesite = root / 'packagesite'
        if packagesite.exists():
            shutil.rmtree(packagesite)
        packagesite.mkdir(parents=True)
        with open(packagesite / 'packagesite.yaml', "wb") as yaml:
            for package in self.__packages:
                package._export_to_site(yaml)

        self.__archive(packagesite, 'packagesite.yaml', signer, now)
        if not keep_expanded:
            shutil.rmtree(packagesite)

        data = root / 'data'
        if data.exists():
            shutil.rmtree(data)
        data.mkdir(parents=True)
        with open(data / 'data', 'w', encoding='utf-8') as datafile:
            content = {'groups': [], 'packages': []}
            for package in self.__packages:
                package._export_to_data(content['packages'])
            json.dump(content, datafile, separators=(',', ':'))

        self.__archive(data, 'data', signer, now)
        if not keep_expanded:
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
        
        all_folder = root / 'All'
        if all_folder.exists():
            shutil.rmtree(all_folder)
        all_folder.mkdir(parents=True)
        for package in self.__packages:
            dest = all_folder / package.repo_filename
            shutil.copy2(package.src_path, dest)


    @staticmethod
    def __archive(directory: Path, filename: str, signer: PkiSigner, now: datetime):
        signature = signer.get_free_bsd_signature(directory / filename)
        with open(directory / 'signature', 'wb') as sig_file:
            sig_file.write(signature)


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

