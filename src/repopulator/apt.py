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
import tarfile
import arpy

from functools import total_ordering
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import AbstractSet, Any, BinaryIO, Dict, KeysView, Mapping, Optional, Sequence

from .pgp_signer import PgpSigner
from .util import NoPublicConstructor, PackageParsingException, VersionKey, ensure_one_line_str, lower_bound, file_digest, path_from_pathlike


class AptPackage(metaclass=NoPublicConstructor):
    """A package in AptRepo"""

    @classmethod
    def _load(cls, src_path: Path, repo_filename: str) -> AptPackage:
        fields: Dict[str, str | list[str]] = {}
        with arpy.Archive(str(src_path)) as ar:
            it = iter(ar)
            first_file = next(it)
            if first_file.header.name != b'debian-binary':
                raise PackageParsingException(f'{src_path} is not a valid Debian archive: debian-binary missing')
            second_file = next(it)
            if not second_file.header.name.startswith(b'control.'): # type: ignore
                raise PackageParsingException(f'{src_path} is not a valid Debian archive: no control archive')
            with tarfile.open(name=second_file.header.name, fileobj=second_file, mode="r") as control_archive: # type: ignore
                control_file = None
                try:
                    control_file = control_archive.extractfile('./control')
                except KeyError:
                    pass
                if control_file is None:
                    raise PackageParsingException(f'{src_path} is not a valid Debian archive: no control file')
                last_key = None
                for line in control_file: # type: ignore
                    line = line.decode().rstrip()
                    if len(line) == 0:
                        break
                    if last_key is not None and (line.startswith(' ') or line.startswith('\t')):
                        last_val = fields[last_key]
                        if isinstance(last_val, list):
                            last_val.append(line[1:])
                        else:
                            fields[last_key] = [last_val, line[1:]]
                    else:
                        sep_idx = line.find(':')
                        if sep_idx < 1:
                            raise PackageParsingException(f'{src_path} is not a valid Debian archive: line `{line}` in control file is invalid')
                        key = line[0:sep_idx]
                        value = line[sep_idx + 1:].strip()
                        fields[key] = value
                        last_key = key
                if (name := fields.get('Package')) is None:
                    raise PackageParsingException(f'{src_path} is not a valid Debian archive: Package field is missing')
                if not isinstance(name, str):
                    raise PackageParsingException(f'{src_path} is not a valid Debian archive: Package field has invalid value')

                if (arch := fields.get('Architecture')) is None:
                    raise PackageParsingException(f'{src_path} is not a valid Debian archive: Architecture field is missing')
                if not isinstance(arch, str):
                    raise PackageParsingException(f'{src_path} is not a valid Debian archive: Architecture field has invalid value')

                if (ver := fields.get('Version')) is None:
                    raise PackageParsingException(f'{src_path} is not a valid Debian archive: Version field is missing')
                if not isinstance(ver, str):
                    raise PackageParsingException(f'{src_path} is not a valid Debian archive: Version field has invalid value')
            
            
            fields['Filename'] = repo_filename
            fields['Size'] = str(src_path.stat().st_size)
            hashes = [
                (hashlib.md5, 'MD5sum'),
                (hashlib.sha1, 'SHA1'),
                (hashlib.sha256, 'SHA256'),
                (hashlib.sha512, 'SHA512'),
            ]
            for hash_func, name in hashes:
                with open(src_path, "rb") as pack_file:
                    digest = file_digest(pack_file, hash_func)
                fields[name] = digest.hexdigest()

        return cls._create(src_path, fields)
    
    def __init__(self, src_path: Path, fields: Dict[str, str | list[str]]):
        """Internal, do not use.
        Use AptRepo.add_package to create instances of this class
        """
        self.__src_path = src_path
        self.__fields = fields
        self.__version_key = VersionKey.parse(fields['Version']) # type: ignore
        

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__fields['Package']  # type: ignore
    
    @property
    def version_str(self) -> str:
        """Version of the package as a string"""
        return self.__fields['Version']  # type: ignore
    
    @property
    def version_key(self) -> VersionKey:
        """Version of the package as a properly comparable key"""
        return self.__version_key
    
    @property
    def arch(self) -> str:
        """Architecture of the package"""
        return self.__fields['Architecture']  # type: ignore
    
    @property
    def fields(self) -> Mapping[str, Any]:
        """Information about package stored in the repository index"""
        return self.__fields
    
    @property
    def repo_filename(self) -> str:
        """Filename of the package when stored inside the repository"""
        return self.__fields['Filename'] # type: ignore
    
    @property
    def src_path(self) -> Path:
        """Path to the original package file"""
        return self.__src_path



    def _write_index_entry(self, f: BinaryIO):
        for key, value in self.__fields.items():
            if isinstance(value, str):
                f.write(f'{key}: {value}\n'.encode())
            else:
                f.write(f'{key}: {value[0]}\n'.encode())
                for i in range(1, len(value)):
                    f.write(f' {value[i]}\n'.encode())


@total_ordering
class AptDistribution(metaclass=NoPublicConstructor):
    """A distribution in AptRepo
    
    Attributes:
        origin (Optional[str]): Origin of the distribution
        label (Optional[str]): Label of the distribution
        suite (Optional[str]): Suite of the distribution
        codename (Optional[str]): Codename of the distribution
        version (Optional[str]): Version of the distribution
        description (Optional[str]): Description of the distribution
    """

    @classmethod
    def _new(cls,
             path: PurePosixPath,
             origin: Optional[str],
             label: Optional[str],
             suite: Optional[str],
             codename: Optional[str],
             version: Optional[str],
             description: Optional[str]) -> AptDistribution:
        return cls._create(path, origin, label, suite, codename, version, description)

    def __init__(self, 
                 path: PurePosixPath,
                 origin: Optional[str],
                 label: Optional[str],
                 suite: Optional[str],
                 codename: Optional[str], 
                 version: Optional[str],
                 description: Optional[str]) -> None:
        """Internal, do not use.
        Use AptRepo.add_distribution to create instances of this class
        """

        self.__path = path
        self.origin = origin
        self.label = label
        self.suite = suite
        self.codename = codename
        self.version = version
        self.description = description

        self.__packages: Dict[str, Dict[str, list[AptPackage]]] = {}

    def __hash__(self):
        return hash(self.__path)
    
    def __eq__(self, other: object):
        if isinstance(other, AptDistribution):
            return self.__path == other.__path
        return NotImplemented
    
    def __lt__(self, other):
        return self.__path < other.__path
    
    @property
    def path(self) -> PurePosixPath:
        """Path of the distribution"""
        return self.__path
    
    @property
    def components(self) -> KeysView[str]:
        """Components in this distribution"""
        return self.__packages.keys() 
    
    def architectures(self, component: str) -> KeysView[str]:
        """Architectures for a given component"""
        return self.__packages[component].keys() 
    
    def packages(self, component: str, arch: str) -> Sequence[AptPackage]:
        """Architectures for a given component and architecture"""
        return self.__packages[component][arch]
    
    def __repr__(self):
        return f"{self.__path} distribution)"
    
    @staticmethod
    def _package_key(p: AptPackage): 
        return (p.name, p.version_str) # apt tools seem to sort by string

    def _add_package(self, package: AptPackage, component: str):
        arch = package.arch
        archs = self.__packages.setdefault(component, {})
        packages = archs.setdefault(arch, [])
        
        idx = lower_bound(packages, package, lambda x, y: self._package_key(x) < self._package_key(y))
        if idx < len(packages) and self._package_key(packages[idx]) == self._package_key(package):
            raise ValueError(f'Duplicate package for {self.__path}, {component}, {arch}')
        packages.insert(idx, package)

    def _remove_package(self, package: AptPackage, component: Optional[str] = None):
        if component is None:
            components = list(self.__packages)
        else:
            components = [component]
        for current_component in components:
            archs = self.__packages.get(current_component)
            if archs is None:
                continue
            packages = archs.get(package.arch)
            if packages is None:
                continue
            idx = lower_bound(packages, package, lambda x, y: self._package_key(x) < self._package_key(y))
            if idx < len(packages) and packages[idx] is package:
                del packages[idx]
                if len(packages) == 0:
                    del archs[package.arch]
                    if len(archs) == 0:
                        del self.__packages[current_component]

    def _export(self, root: Path, signer: PgpSigner, now: Optional[datetime] = None):
        if now is None:
            now = datetime.now(timezone.utc)
        
        dist_dir = root / self.__path
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        dist_dir.mkdir(parents=True)

        components = []
        archs = []
        for comp, comp_archs in self.__packages.items():
            components.append(comp)
            for arch in comp_archs:
                archs.append(arch)
        components.sort()
        archs.sort()

        package_indices: Sequence[Path] = []
        for comp in components:
            for arch in archs:
                pack, pack_gz = self.__export_packages(dist_dir, comp, arch, now)
                package_indices += [pack, pack_gz]

        Release_path = dist_dir / 'Release' # pylint: disable=invalid-name
        with open(Release_path, "wb") as f:
            if self.origin is not None:
                f.write(f'Origin: {self.origin}\n'.encode())
            if self.label is not None:
                f.write(f'Label: {self.label}\n'.encode())
            if self.suite is not None:
                f.write(f'Suite: {self.suite}\n'.encode())
            else:
                f.write(f'Suite: {self.__path.name}\n'.encode())
            if self.codename is not None:
                f.write(f'Codename: {self.codename}\n'.encode())
            else:
                f.write(f'Codename: {self.__path.name}\n'.encode())
            if self.version is not None:
                f.write(f'Version: {self.version}\n'.encode())
            f.write(f'Architectures: {",".join(archs)}\n'.encode())
            f.write(f'Components: {",".join(components)}\n'.encode())
            if self.description is not None:
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
                for package_index in package_indices:
                    with open(package_index, "rb") as pack_file:
                        digest = file_digest(pack_file, hashFunc)
                    f.write(f' {digest.hexdigest()} {package_index.stat().st_size: >16} {package_index.relative_to(dist_dir).as_posix()}\n'.encode())
        
        os.utime(Release_path, (now.timestamp(), now.timestamp()))

        InRelease_path = dist_dir / 'InRelease' # pylint: disable=invalid-name
        signer.sign_inline(Release_path, InRelease_path)
        os.utime(InRelease_path, (now.timestamp(), now.timestamp()))
        Release_pgp_path = Release_path.with_suffix('.pgp') # pylint: disable=invalid-name
        signer.sign_external(Release_path, Release_pgp_path)
        os.utime(Release_pgp_path, (now.timestamp(), now.timestamp()))
        
            
            
    def __export_packages(self, dist_root: Path, component: str, arch: str, now: datetime):
        packages_dir = dist_root / component / f'binary-{arch}'
        if packages_dir.exists():
            shutil.rmtree(packages_dir)
        packages_dir.mkdir(parents=True)

        Packages_path = packages_dir / 'Packages' # pylint: disable=invalid-name
        with open(Packages_path, "wb") as f:
            packages = self.__packages.get(component, {}).get(arch, [])
            if len(packages) > 0:
                packages[0]._write_index_entry(f)
            for package in packages[1:]:
                f.write(b'\n')
                package._write_index_entry(f)
        os.utime(Packages_path, (now.timestamp(), now.timestamp()))

        Packages_gz_path = Packages_path.with_suffix('.gz') # pylint: disable=invalid-name
        with open(Packages_path, 'rb') as f_in:
            with open(Packages_gz_path, 'wb') as f_out:
                with gzip.GzipFile(filename=Packages_path.name, mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                    shutil.copyfileobj(f_in, f_zip)
        os.utime(Packages_gz_path, (now.timestamp(), now.timestamp()))

        return (Packages_path, Packages_gz_path)

class AptRepo:
    """Generates APT repositories"""

    def __init__(self):
        """Constructor for AptRepo class"""
        self.__distributions: set[AptDistribution] = set()
        self.__packages: list[AptPackage] = []

    def add_distribution(self,
                         path: PurePosixPath | str,
                         *,
                         origin: Optional[str]=None,
                         label: Optional[str]=None,
                         suite: Optional[str]=None,
                         codename: Optional[str]=None,
                         version: Optional[str]=None,
                         description: Optional[str]=None) -> AptDistribution:
        """Adds a new distribution to the repository

        Args:
            path: distribution "name" inside the repo (e.g. 'jammy' or 'focal'), which is also its path.
            origin: 'Origin' field. See https://wiki.debian.org/DebianRepository/Format#Origin
            label: 'Label' field. See https://wiki.debian.org/DebianRepository/Format#Label
            suite: 'Suite' field. See https://wiki.debian.org/DebianRepository/Format#Suite If omitted, Suite is
                set to the last component of the path
            codename: 'Codename' field. See https://wiki.debian.org/DebianRepository/Format#Codename If omitted, Codename is
                set to the last component of the path
            version: 'Version' field. See https://wiki.debian.org/DebianRepository/Format#Version
            description: 'Description' field. A description of the distribution

        Returns:
            a new AptDistribution object

        """
        path = path if isinstance(path, PurePosixPath) else PurePosixPath(path)
        if path.is_absolute():
            raise ValueError('path value must be a relative path')
        if origin is not None:
            origin = ensure_one_line_str(origin, 'origin')
        if label is not None:
            label = ensure_one_line_str(label, 'label')
        if suite is not None:
            suite = ensure_one_line_str(suite, 'suite')
        if codename is not None:
            codename = ensure_one_line_str(codename, 'codename')
        if version is not None:
            version = ensure_one_line_str(version, 'version')
        if description is not None:
            description = ensure_one_line_str(description, 'description')
        dist = AptDistribution._new(path, origin=origin, label=label, suite=suite, codename=codename, 
                                    version=version, description=description)
        if dist in self.__distributions:
            raise ValueError('Duplicate distribution')
        self.__distributions.add(dist)
        return dist
    
    def del_distribution(self, dist: AptDistribution):
        """Removes a distribution from the repository.

        If the distribution is not in this repo the function ignores it and succeeds

        Params:
            dist: the distribution to remove
        """
        try:
            self.__distributions.remove(dist)
        except KeyError:
            pass

    def add_package(self, path: str | os.PathLike[str]) -> AptPackage:
        """Adds a package to the repository

        Adding a package to the repository simply adds it to the pool of available packages.
        After doing that you need to add the returned package to one or more distributions to make it available
        to repository clients.

        Args:
            path: the path to `.deb` file for the package.
        Returns:
            an AptPackage object for the added package
        """

        path = path_from_pathlike(path)
        package = AptPackage._load(path, path.name)
        idx = lower_bound(self.__packages, package, lambda x, y: x.repo_filename < y.repo_filename)
        if idx < len(self.__packages) and self.__packages[idx].repo_filename == package.repo_filename:
            raise ValueError('Duplicate package')
        self.__packages.insert(idx, package)
        return package
    
    def del_package(self, package: AptPackage):
        """Removes a package from this repository

        The package is removed from the repository and all distributions in it. 
        It is not an error to pass a package that is not in a repository to this function.
        It will be ignored in such case.

        Args:
            package: the package to remove
        """
        idx = lower_bound(self.__packages, package, lambda x, y: x.repo_filename < y.repo_filename)
        if idx < len(self.__packages) and self.__packages[idx] is package:
            for dist in self.__distributions:
                dist._remove_package(package)
            del self.__packages[idx]
    
    def assign_package(self, package: AptPackage, dist: AptDistribution, component: str):
        """Assigns a repository package to a distribution's component

        Args:
            package: the package to assign. 
            dist: the distribution to assign to
            component: the distribution's component to assign the package to
        """
        if package not in self.__packages:
            raise ValueError('package is not in repository')
        if dist not in self.__distributions:
            raise ValueError('distribution is not in repository')
        dist._add_package(package, component)

    def unassign_package(self, package: AptPackage, dist: AptDistribution, component: Optional[str] = None):
        """Removes a repository package from a distribution's component

        If the package or distribution are not in this repository or the package is not 
        assigned to the distribution's component the call is silently ignored.

        Args:
            package: the package to remove. 
            dist: the distribution to remove from
            component: if specified remove the package only from this component. Otherwise, remove it from all
        """

        if package not in self.__packages:
            return
        if dist not in self.__distributions:
            return
        dist._remove_package(package, component)
    

    @property
    def distributions(self) -> AbstractSet[AptDistribution]:
        """Distributions in this repository"""
        return self.__distributions
    
    @property
    def packages(self) -> Sequence[AptPackage]:
        """Packages in this repository"""
        return self.__packages
    
    def export(self, root: str | os.PathLike[str], signer: PgpSigner, now: Optional[datetime] = None):
        """Export the repository into a given folder.

        This actually creates an on-disk repository suitable to serve to APT clients. If the directory to export to
        already exists the export process tries to handle pre-existing content there gracefully. Content that doesn't
        conflict with repository content will be left alone. Content that does conflict will be removed or overwritten.

        Specifically:

        * any existing pool/*.deb files will be removed and replaced with the ones from the repository.
        * 'dists' subdirectory will be completely erased and replaced with exported content

        Args:
            root: the root path to export to. The directory will be created if it does not exist
            signer: A PgpSigner instance to use for signing the repository.
            now: optional timestamp to use when generating files (including various timestamp fields *inside* files).
                Specifying this argument allows for reproducible repository creation.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        root = path_from_pathlike(root)
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
            dest = pool / package.repo_filename
            shutil.copy2(package.src_path, dest)
        
