# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""Generating DNF/YUM RPM repositories"""

from __future__ import annotations

import os
import shutil
import gzip
import hashlib
import stat
import re
import collections.abc
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone
from functools import total_ordering
from typing import Any, Callable, Optional, Sequence, Tuple

from .rpmfile import open as rpmfile_open

from .pgp_signer import PgpSigner
from .util import ImmutableDict, NoPublicConstructor, find_if, lower_bound, VersionKey, file_digest, indent_tree, path_from_pathlike

_RPMSENSE_ANY           = 0
_RPMSENSE_LESS          = 1 << 1
_RPMSENSE_GREATER       = 1 << 2
_RPMSENSE_EQUAL         = 1 << 3
_RPMSENSE_PROVIDES      = 1 << 4
_RPMSENSE_POSTTRANS     = 1 << 5
_RPMSENSE_PREREQ        = 1 << 6
_RPMSENSE_PRETRANS      = 1 << 7
_RPMSENSE_INTERP        = 1 << 8
_RPMSENSE_SCRIPT_PRE    = 1 << 9
_RPMSENSE_SCRIPT_POST   = 1 << 10
_RPMSENSE_SCRIPT_PREUN  = 1 << 11
_RPMSENSE_SCRIPT_POSTUN = 1 << 12
_RPMSENSE_SCRIPT_VERIFY = 1 << 13
_RPMSENSE_FIND_REQUIRES = 1 << 14
_RPMSENSE_FIND_PROVIDES = 1 << 15
_RPMSENSE_TRIGGERIN     = 1 << 16
_RPMSENSE_TRIGGERUN     = 1 << 17
_RPMSENSE_TRIGGERPOSTUN = 1 << 18
_RPMSENSE_MISSINGOK     = 1 << 19
_RPMSENSE_RPMLIB        = 1 << 24
_RPMSENSE_TRIGGERPREIN  = 1 << 25
_RPMSENSE_KEYRING       = 1 << 26
_RPMSENSE_CONFIG        = 1 << 28

_RPMFILE_NONE       = 0
_RPMFILE_CONFIG     = 1 <<  0	    # from %%config
_RPMFILE_DOC        = 1 <<  1     # from %%doc
_RPMFILE_ICON       = 1 <<  2     # from %%donotuse
_RPMFILE_MISSINGOK  = 1 <<  3     # from %%config(missingok)
_RPMFILE_NOREPLACE  = 1 <<  4     # from %%config(noreplace)
_RPMFILE_SPECFILE   = 1 <<  5     # @todo (unnecessary) marks 1st file in srpm.
_RPMFILE_GHOST      = 1 <<  6     # from %%ghost
_RPMFILE_LICENSE    = 1 <<  7     # from %%license
_RPMFILE_README     = 1 <<  8     # from %%readme
# bits 9-10 unused
_RPMFILE_PUBKEY     = 1 << 11     # from %%pubkey
_RPMFILE_ARTIFACT   = 1 << 12     # from %%artifact


_ABI_VERSION_PATTERN = re.compile(r'([^(]+)\(([^)]*)\)')

def _compare_abi_version(dep1: str, dep2: str):
    """
    Compares two library dependencies with ABI part by ABI version

    libc.so.6() < libc.so.6(GLIBC_2.3.4)(64 bit) < libc.so.6(GLIBC_2.4)
    Return values: 0 - same; 1 - first is bigger; -1 - second is bigger; None - error

    Error is returned when the libraries name prefixes without ABI aren't the same
    """

    if dep1 == dep2: return 0

    m1 = _ABI_VERSION_PATTERN.search(dep1)
    m2 = _ABI_VERSION_PATTERN.search(dep2)

    if m1 is None: 
        if m2 is None or m2.group(1) != dep1: 
            return None
        return -1
    if m2 is None:
        if m1.group(1) != dep2:
            return None
        return 1
    
    if m1.group(1) != m2.group(1):
        return None
        
    ver1 = VersionKey.parse(m1.group(2))
    ver2 = VersionKey.parse(m2.group(2))

    return (ver1 > ver2) - (ver1 < ver2)


@total_ordering
class RpmVersion:
    """Representation of RPM package version

    Instances of this class are properly comparable (`==`, `!=`, `<`, `<=`, `>`, `>=`) and hashable.

    The string representation of an RpmVersion object is the properly formatted version string
    """
    def __init__(self, version: str | Sequence[str]) -> None:
        """Constructor for RpmVersion class

        Args:
            version: either the full RPM version in string form or a tuple of (epoch, version, release)
        """
        if isinstance(version, str):
            if (colon_pos := version.find(':')) != -1:
                self.epoch = str(int(version[:colon_pos]))
                version = version[colon_pos+1:]
            else:
                self.epoch = "0"
            ver_parts = version.split('-', 2)
            self.ver = ver_parts[0]
            self.rel = ver_parts[1] if len(ver_parts) == 2 else None
        elif isinstance(version, collections.abc.Sequence):
            if len(version) not in (2, 3):
                raise ValueError('version sequence must have 2 or 3 elements')
            self.epoch = version[0] 
            self.ver = version[1] 
            self.rel = version[2] if len(version) == 3 else None 
        else:
            raise ValueError('version must be a string or a 3-element sequence')
        self.__keys = (
            VersionKey.parse(self.epoch), 
            VersionKey.parse(self.ver),
            VersionKey.parse(self.rel) if self.rel is not None else VersionKey(0)
        )

    def __eq__(self, other):
        if isinstance(other, RpmVersion):
            return self.__keys == other.__keys
        return NotImplemented
    
    def __hash__(self):
        return hash(self.__keys)
    
    def __lt__(self, other):
        if isinstance(other, RpmVersion):
            return self.__keys < other.__keys
        return NotImplemented
    
    def __str__(self) -> str:
        ret = self.epoch + ':' if self.epoch != "0" else ''
        ret += self.ver
        if self.rel is not None:
            ret += f'-{self.rel}'
        return ret
    
class _RpmFile:
    # pylint: disable=missing-function-docstring
    def __init__(self, basename: str, dirname: str, flags: int, mode: int):
        self.basename = basename
        self.dirname = dirname
        self.flags = flags
        self.mode = mode

    def path(self) -> str:
        return self.dirname + self.basename

    def type(self) -> Optional[str]:
        if stat.S_ISDIR(self.mode & 0xFFFF):
            return "dir"
        if self.flags & _RPMFILE_GHOST != 0:
            return "ghost"
        return None
    
    def is_primary(self):
        if self.dirname.startswith("/etc/"):
            return True
        if self.dirname.startswith("/usr/lib/sendmail"):
            return True
        if self.dirname.find("bin/") != -1:
            return True
        return False
    
    def export(self) -> ET.Element:
        file = ET.Element('file')
        file.text = self.path()
        if (tp := self.type()) is not None:
            file.set("type", tp)
        return file
    

class _RpmDependency:
    # pylint: disable=missing-function-docstring
    def __init__(self, name: str, flags: int, version: str) -> None:
        self.name = name
        self.flags = flags
        self.version = RpmVersion(version)
        

    def comparison(self):
        flags = self.flags & 0xf

        if flags == _RPMSENSE_LESS:                           return "LT"
        if flags == _RPMSENSE_GREATER:                        return "GT"
        if flags == _RPMSENSE_EQUAL:                          return "EQ"
        if flags == (_RPMSENSE_LESS | _RPMSENSE_EQUAL):       return "LE"
        if flags == (_RPMSENSE_GREATER | _RPMSENSE_EQUAL):    return "GE"
        
        return None
    
    def pre(self):
        return (self.flags & (_RPMSENSE_PREREQ |
                              _RPMSENSE_SCRIPT_PRE |
                              _RPMSENSE_POSTTRANS |
                              _RPMSENSE_PRETRANS |
                              _RPMSENSE_SCRIPT_POST)) != 0
    
    def export(self) -> ET.Element:
        el = ET.Element('rpm:entry')
        el.set('name', self.name)
        if self.pre():
            el.set('pre', "1")
        if (comp := self.comparison()) is not None:
            el.set('flags', comp)
            el.set('epoch', self.version.epoch)
            el.set('ver', self.version.ver)
            if self.version.rel is not None:
                el.set('rel', self.version.rel)
        return el


class RpmPackage(metaclass=NoPublicConstructor):
    """A package in RpmRepo"""
    @classmethod
    def _load(cls, src_path: Path, filename: str) -> RpmPackage:
        st = src_path.stat()
        with open(src_path, "rb") as f:
            pkgid = file_digest(f, hashlib.sha256).hexdigest()
        with rpmfile_open(src_path) as rpm:
            headers = rpm.headers
            header_range = rpm.header_range
        return cls._create(src_path, filename, pkgid, st.st_size, int(st.st_mtime), headers, header_range)

    def __init__(self, src_path: Path, filename: str, pkgid: str, size: int, mtime: int,
                 headers: dict[str, Any], header_range: tuple[int, int]):
        """Internal, do not use
        Use RpmRepo.addPackage to create instances of this class
        """
        self.__src_path = src_path
        self.__filename = filename
        self.__pkgid = pkgid
        self.__headers = headers
        self.__name: str = self.__headers['name'].decode()
        self.__arch: str = self.__headers['arch'].decode()
        self.__version = RpmVersion((self.__headers.get('serial', '0'),
                                     self.__headers['version'].decode(),
                                     self.__headers['release'].decode()))
        
        primary_files = self.__fill_files()
        self.__fill_primary(filename, size, mtime, primary_files, header_range)
        self.__fill_changelog()

    @property
    def name(self) -> str:
        """Name of the package"""
        return self.__name
    
    @property
    def version_str(self) -> str:
        """Version of the package as a string"""
        return str(self.__version)
    
    @property
    def version_key(self) -> RpmVersion:
        """Version of the package as a properly comparable key"""
        return self.__version
    
    @property
    def arch(self) -> str:
        """Architecture of the package"""
        return self.__arch
    
    @property
    def pkgid(self) -> str:
        """Unique identifier of the package in the repository"""
        return self.__pkgid
    
    @property
    def fields(self) -> ImmutableDict:
        """Information about package stored in the repository index"""
        return ImmutableDict(self.__headers)
    
    @property
    def repo_filename(self) -> str:
        """Filename of the package when stored inside the repository"""
        return self.__filename
    
    @property
    def src_path(self) -> Path:
        """Path to the original package file"""
        return self.__src_path
    
    def _append_filelist(self, parent: ET.Element):
        parent.append(self.__filelist) #should we clone it?

    def _append_changelog(self, parent: ET.Element):
        parent.append(self.__changelog) #should we clone it?

        
    def __fill_files(self) -> list[_RpmFile]:
        headers = self.__headers

        self.__filelist = ET.Element('package')
        self.__filelist.set('pkgid', self.pkgid)
        self.__filelist.set('name', self.name)
        self.__filelist.set('arch', self.arch)
        version = ET.SubElement(self.__filelist, 'version')
        version.set('epoch', self.version_key.epoch)
        version.set('ver', self.version_key.ver)
        assert self.version_key.rel is not None
        version.set('rel', self.version_key.rel)

        primary_files: list[_RpmFile] = []
        dirnames = self.__read_list(headers, 'dirnames')
        for basename, dirindex, flags, mode in zip(self.__read_list(headers, 'basenames'),
                                                   self.__read_list(headers, 'dirindexes'),
                                                   self.__read_list(headers, 'fileflags'),
                                                   self.__read_list(headers, 'filemodes')):
            file = _RpmFile(basename.decode(), dirnames[dirindex].decode(), flags, mode)
            self.__filelist.append(file.export())
            if file.is_primary():
                primary_files.append(file)

        return primary_files

    def __fill_primary(self, filename: str, size: int, mtime: int, primary_files: Sequence[_RpmFile], header_range: Tuple[int, int]):
        headers = self.__headers

        self.primary = ET.Element('package')
        self.primary.set('type', 'rpm')
        ET.SubElement(self.primary, 'name').text = headers['name'].decode()
        ET.SubElement(self.primary, 'arch').text = headers['arch'].decode()
        version = ET.SubElement(self.primary, 'version')
        version.set('epoch', self.version_key.epoch)
        version.set('ver', self.version_key.ver)
        assert self.version_key.rel is not None
        version.set('rel', self.version_key.rel)
        checksum = ET.SubElement(self.primary, 'checksum')
        checksum.set('type', 'sha256')
        checksum.set('pkgid', 'YES')
        checksum.text = self.pkgid 
        ET.SubElement(self.primary, 'summary').text = headers.get('summary', b'').decode()
        ET.SubElement(self.primary, 'description').text = headers.get('description', b'').decode()
        ET.SubElement(self.primary, 'packager').text = headers.get('packager', b'').decode()
        ET.SubElement(self.primary, 'url').text = headers.get('url', b'').decode()
        time = ET.SubElement(self.primary, 'time')
        time.set('file', str(mtime))
        if (buildtime := headers.get('buildtime')) is not None:
            time.set('build', str(buildtime))
        size_el = ET.SubElement(self.primary, 'size')
        size_el.set('package', str(size))
        size_el.set('installed', str(headers.get('longsize', headers['size'])))
        size_el.set('archive', str(headers.get('longarchivesize',
                                            headers.get('archivesize', headers['payloadsize']))))
        ET.SubElement(self.primary, 'location').set('href', filename)
        fmt = ET.SubElement(self.primary, 'format')
        if (license_ := headers.get('copyright')) is not None:
            ET.SubElement(fmt, 'rpm:license').text = license_.decode()
        if (vendor := headers.get('vendor')) is not None:
            ET.SubElement(fmt, 'rpm:vendor').text = vendor.decode()
        if (group := headers.get('group')) is not None:
            ET.SubElement(fmt, 'rpm:group').text = group.decode()
        if (buildhost := headers.get('buildhost')) is not None:
            ET.SubElement(fmt, 'rpm:buildhost').text = buildhost.decode()
        if (sourcerpm := headers.get('sourcerpm')) is not None:
            ET.SubElement(fmt, 'rpm:sourcerpm').text = sourcerpm.decode()
        header_range_el = ET.SubElement(fmt, 'rpm:header-range')
        header_start, header_end = header_range
        header_range_el.set('start', str(header_start))
        header_range_el.set('end', str(header_end))

        provided = self.__collect_dependencies(headers, ('provides', 'provideflags', 'provideversion'))
        self.__write_dependencies(fmt, 'rpm:provides', provided)
        
        required_filter = self._RequiredFilter(provided, primary_files)
        required = self.__collect_dependencies(headers, ('requirename', 'requireflags', 'requireversion'),
                                               filter_func=required_filter)
        if required_filter.latest_libc is not None:
            required.append(required_filter.latest_libc)
        
        self.__write_dependencies(fmt, 'rpm:requires', required)
            

        simple_refs = [
            ('rpm:conflicts',   ('conflictname',    'conflictflags',    'conflictversion')),
            ('rpm:obsoletes',   ('obsoletes',       'obsoleteflags',    'obsoleteversion')),
            ('rpm:suggests',    ('suggestname',     'suggestflags',     'suggestversion')),
            ('rpm:enhances',    ('enhancename',     'enhanceflags',     'enhanceversion')),
            ('rpm:supplements', ('supplementname',  'supplementflags',  'supplementversion')),
            ('rpm:recommends',  ('recommendname',   'recommendflags',   'recommendversion'))
        ]

        for refs in simple_refs:
            deps = self.__collect_dependencies(headers, refs[1])
            self.__write_dependencies(fmt, refs[0], deps)
            
        for file in primary_files:
            self.primary.append(file.export())


    class _RequiredFilter:
        def __init__(self, provided: Sequence[_RpmDependency], primary_files: Sequence[_RpmFile]):
            self.provided = provided
            self.primary_files = primary_files
            self.latest_libc: Optional[_RpmDependency] = None

        def __call__(self, all_deps: Sequence[_RpmDependency], dep: _RpmDependency) -> bool:
            if dep.name.startswith('rpmlib('):
                return False
            if find_if(self.provided, dep, lambda x, y: x.name == y.name):
                return False
            if (dep.name.startswith('/') and 
                    find_if(self.primary_files, dep, lambda f, n: f.is_primary() and f.path() == n.name) is not None):
                return False
            if find_if(all_deps, dep, lambda x, y: (
                                            x.name == y.name and 
                                            x.version == y.version and
                                            x.comparison() == y.comparison() and
                                            x.pre() == y.pre())) is not None:
                return False
            if dep.name.startswith('libc.so.6'):
                if (self.latest_libc is None or 
                        _compare_abi_version(dep.name, self.latest_libc.name) == 1):
                    self.latest_libc = dep
                return False
            return True


    def __collect_dependencies(self, headers, desc: Tuple[str, str, str],
                               filter_func: Optional[Callable[[Sequence[_RpmDependency], _RpmDependency], bool]] = None):
        deps: list[_RpmDependency] = []
        for name, flags, version in zip(self.__read_list(headers, desc[0]),
                                        self.__read_list(headers, desc[1]),
                                        self.__read_list(headers, desc[2])):
            dep = _RpmDependency(name.decode(), flags, version.decode())
            if filter_func is not None and not filter_func(deps, dep):
                continue
            deps.append(dep)
        return deps

    @staticmethod
    def __write_dependencies(parent: ET.Element, name: str, deps: Sequence[_RpmDependency]):
        if len(deps) > 0:
            ret = ET.SubElement(parent, name)
            for dep in deps:
                ret.append(dep.export())

    def __fill_changelog(self):
        headers = self.__headers

        self.__changelog = ET.Element('package')
        self.__changelog.set('pkgid', self.pkgid)
        self.__changelog.set('name', self.name)
        self.__changelog.set('arch', self.arch)
        version = ET.SubElement(self.__changelog, 'version')
        version.set('epoch', self.version_key.epoch)
        version.set('ver', self.version_key.ver)
        assert self.version_key.rel is not None
        version.set('rel', self.version_key.rel)

        entries = []
        for time, author, comment in zip(self.__read_list(headers, 'changelogtime'),
                                         self.__read_list(headers, 'authors'),
                                         self.__read_list(headers, 'comments')):
            entry = ET.Element('changelog')
            entry.text = comment.decode()
            entry.set('author', author.decode())
            entry.set('date', str(time))
            entries.append(entry)
        
        entries.sort(key=lambda x: int(x.get('date')))

        for entry in entries[-10:]:
            self.__changelog.append(entry)


    
    @staticmethod
    def __read_list(headers: dict[str, Any], name: str):
        ret = headers.get(name)
        if ret is None: return []
        if not isinstance(ret, list) and not isinstance(ret, tuple): return [ret]
        return ret



class RpmRepo:
    """Generates RPM repositories"""

    def __init__(self):
        """Constructor for RpmRepo class"""
        self.__packages: list[RpmPackage] = []

    def add_package(self, path: str | os.PathLike[str]) -> RpmPackage:
        """Adds a package to the repository

        Args:
            path: the path to `.rpm` file for the package.
        Returns:
            an RpmPackage object for the added package
        """
        path = path_from_pathlike(path)
        package = RpmPackage._load(path, path.name)
        for existing in self.__packages:
            if existing.pkgid == package.pkgid:
                raise ValueError("duplicate package id")
        
        idx = lower_bound(self.__packages, package, lambda x, y: self._package_key(x) < self._package_key(y))
        if idx < len(self.__packages) and self._package_key(self.__packages[idx]) == self._package_key(package):
            raise ValueError('Duplicate package')
        self.__packages.insert(idx, package)
        return package
    
    def del_package(self, package: RpmPackage):
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
    def _package_key(p: RpmPackage): 
        return (p.name, p.version_key, p.arch)
    
    @property
    def packages(self) -> Sequence[RpmPackage]:
        """Packages in the repository"""
        return self.__packages

    def export(self, root: str | os.PathLike[str], signer: PgpSigner, now: Optional[datetime] = None, keep_expanded: bool = False):
        """Export the repository into a given folder

        This actually creates an on-disk repository suitable to serve to `pacman` clients. If the directory to export to
        already exists the export process tries to handle pre-existing content there gracefully. Content that doesn't
        conflict with repository content will be left alone. Content that does conflict will be removed or overwritten.

        Specifically any existing *.rpm files will be removed and replaced with the ones from the repository.

        Args:
            root: the root path to export to. The directory will be created if it does not exist
            signer: A PgpSigner instance to use for signing the repository.
            now: optional timestamp to use when generating files (including various timestamp fields *inside* files).
                Specifying this argument allows for reproducible repository creation.
            keep_expanded: keep intermediate uncompressed files on disk. This is useful for testing and
                troubleshooting only
        """

        if now is None:
            now = datetime.now(timezone.utc)
        
        root = path_from_pathlike(root)
        repodata = root / 'repodata'
        if repodata.exists():
            shutil.rmtree(repodata)
        repodata.mkdir(parents=True)

        repomd = ET.Element('repomd')
        repomd.set('xmlns', 'http://linux.duke.edu/metadata/repo')
        repomd.set('xmlns:rpm', 'http://linux.duke.edu/metadata/rpm')
        ET.SubElement(repomd, 'revision').text = str(int(now.timestamp()))
        
        primary = ET.SubElement(repomd, 'data')
        primary.set('type', 'primary')
        primary_path = self.__export_primary(repodata)
        os.utime(primary_path, (now.timestamp(), now.timestamp()))
        self.__summarize_file(root, primary_path, primary, now, keep_expanded)

        filelists = ET.SubElement(repomd, 'data')
        filelists.set('type', 'filelists')
        filelists_path = self.__export_filelists(repodata)
        os.utime(filelists_path, (now.timestamp(), now.timestamp()))
        self.__summarize_file(root, filelists_path, filelists, now, keep_expanded)

        other = ET.SubElement(repomd, 'other')
        other_path = self.__export_other(repodata)
        os.utime(other_path, (now.timestamp(), now.timestamp()))
        self.__summarize_file(root, other_path, other, now, keep_expanded)
        
        tree = ET.ElementTree(repomd)
        indent_tree(tree)
        repomd_path = repodata / 'repomd.xml'
        with open(repomd_path, 'wb') as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
        os.utime(repomd_path, (now.timestamp(), now.timestamp()))

        signer.sign_external(repomd_path, repomd_path.parent / (repomd_path.name + '.asc'))

        self.__export_files(root)


    def __export_primary(self, repodata: Path) -> Path:

        metadata = ET.Element('metadata')
        metadata.set('xmlns', 'http://linux.duke.edu/metadata/common')
        metadata.set('xmlns:rpm', 'http://linux.duke.edu/metadata/rpm')
        metadata.set('packages', str(len(self.__packages)))
        for package in self.__packages:
            metadata.append(package.primary) #should we clone it?
        
        tree = ET.ElementTree(metadata)
        indent_tree(tree)
        path = repodata / 'primary.xml'
        with open(path, 'wb') as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
        return path
    
    def __export_filelists(self, repodata: Path) -> Path:
        filelists = ET.Element('filelists')
        filelists.set('xmlns', 'http://linux.duke.edu/metadata/filelists')
        filelists.set('packages', str(len(self.__packages)))
        for package in self.__packages:
            package._append_filelist(filelists)

        tree = ET.ElementTree(filelists)
        indent_tree(tree)
        path = repodata / 'filelists.xml'
        with open(path, 'wb') as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
        return path
    
    def __export_other(self, repodata: Path) -> Path:
        other = ET.Element('otherdata')
        other.set('xmlns', 'http://linux.duke.edu/metadata/other')
        other.set('packages', str(len(self.__packages)))
        for package in self.__packages:
            package._append_changelog(other)

        tree = ET.ElementTree(other)
        indent_tree(tree)
        path = repodata / 'other.xml'
        with open(path, 'wb') as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
        return path

    
    @staticmethod
    def __summarize_file(root: Path, path: Path, parent: ET.Element, now: datetime, keep_expanded: bool):
        gz_path = path.parent / (path.name + '.gz')

        open_st = path.stat()
        with open(path, 'rb') as f_in:
            open_digest = file_digest(f_in, hashlib.sha256)
            f_in.seek(0, 0)
            with open(gz_path, 'wb') as f_out:
                with gzip.GzipFile(filename=path.name, mode='wb', fileobj=f_out, mtime=int(now.timestamp())) as f_zip:
                    shutil.copyfileobj(f_in, f_zip)
            
        os.utime(gz_path, (now.timestamp(), now.timestamp()))
        st = gz_path.stat()
        with open(gz_path, "rb") as f:
            digest = file_digest(f, hashlib.sha256)
        
        checksum = ET.SubElement(parent, 'checksum')
        checksum.set('type', 'sha256')
        checksum.text = digest.hexdigest()
        open_checksum = ET.SubElement(parent, 'open-checksum')
        open_checksum.set('type', 'sha256')
        open_checksum.text = open_digest.hexdigest()
        location = ET.SubElement(parent, 'location')
        location.set('href', gz_path.relative_to(root).as_posix())
        ET.SubElement(parent, 'timestamp').text = str(int(st.st_mtime))
        ET.SubElement(parent, 'size').text = str(st.st_size)
        ET.SubElement(parent, 'open-size').text = str(open_st.st_size)
        if not keep_expanded:
            path.unlink()


    def __export_files(self, root: Path):
        for existing in root.glob('*.rpm'):
            existing.unlink()
        for package in self.__packages:
            dest = root / package.repo_filename
            shutil.copy2(package.src_path, dest)




