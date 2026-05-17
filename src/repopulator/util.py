# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""Internal utilities"""

from __future__ import annotations

import hashlib

import xml.etree.ElementTree as ET

from os import PathLike
from pathlib import Path

from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Type, TypeVar

Key = TypeVar('Key')
Val = TypeVar('Val')
T = TypeVar('T')

def find_if(seq: Sequence[Any], obj: Any, cond: Callable[[Any, Any], bool]):
    """like C++ std::find_if"""
    return next((item for item in seq if cond(item, obj)), None)

def lower_bound(seq: Sequence[Any], obj: Any, comp: Callable[[Any, Any], bool] = lambda x, y: x < y):
    """like C++ std::lower_bound"""
    first = 0
    size = len(seq)
    while size != 0:
        half_way = size // 2
        if comp(seq[first + half_way], obj):
            half_way += 1
            first += half_way
            size -= half_way
        else:
            size = half_way
    return first

class PackageParsingException(Exception):
    """Raised when package parsing fails"""

def path_from_pathlike(arg: str | PathLike[str]):
    """Coerces a pathlike argument to a Path"""
    return Path(arg)

def ensure_str(arg: Any, arg_name: str) -> str:
    """ensures that the arg is str"""
    if isinstance(arg, str):
        return arg
    raise TypeError(f'{arg_name} must be str')

def ensure_one_line_str(arg: Any, arg_name: str) -> str:
    """ensures that the arg is str and has no line breaks"""
    arg = ensure_str(arg, arg_name)
    if arg.find('\n') != -1:
        raise ValueError(f'{arg_name} must not contain line breaks')
    return arg


class VersionKey:
    """Representation of a package version

    Package versions cannot be compared as simple strings. For example, "1.10" should be bigger than
     "1.2". This class allows correct semantic comparisons for versions.

    Instances of this class are properly comparable (`==`, `!=`, `<`, `<=`, `>`, `>=`) and hashable.

    Logically, a version key is a heterogeneous tuple of `str` and `int` elements.
    """

    def __init__(self, *args):
        """
        Constructor for VersionKey class

        Arguments are any number of version parts. Each part can be:

        * a single `int` for a numeric part
        * an `str` or `bytes` object for a string part

        """

        def handle_one(x): 
            if isinstance(x, int) or isinstance(x, str):
                return x
            elif isinstance(x, bytes):
                return x.decode()
            else:
                raise ValueError('VersionKey parts must be integers, strings or bytes')
            
        self.__parts = tuple(handle_one(arg) for arg in args)

    @staticmethod
    def parse(version: str) -> VersionKey:
        """Parses the version key from a string

        Parsing is always well defined for any string and never fails

        Args:
            version: a version string
        Returns: parsed key
        """
        
        def isalpha(c): return ('a' <= c <= 'z') or ('A' <= c <= 'Z')
        def isdigit(c): return '0' <= c <= '9'

        parts: list[int|str] = []
        start_idx = 0
        prev: Optional[Callable[[str], bool]] = None
        for idx in range(0, len(version)):
            c = version[idx]
            
            if prev is not None:
                if prev(c):
                    continue
                substr = version[start_idx: idx]
                parts.append(substr if prev is isalpha else int(substr))
                prev = None
            
            if isalpha(c):
                prev = isalpha
            elif isdigit(c):
                prev = isdigit
            start_idx = idx
        
        if prev is not None:
            substr = version[start_idx:]
            parts.append(substr if prev is isalpha else int(substr))

        ret = VersionKey()
        ret.__parts = tuple(parts)
        return ret

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionKey):
            return NotImplemented
        if len(self.__parts) != len(other.__parts):
            return False
        for my, his in zip(self.__parts, other.__parts):
            mynum = isinstance(my, int)
            hisnum = isinstance(his, int)
            if mynum != hisnum:
                return False
            if my != his:
                return False
        return True
    
    def __ne__(self, other: object):
        res = self.__eq__(other)
        return res if res is NotImplemented else not res
    
    def __hash__(self):
        return hash(self.__parts)
    
    def __lt__(self, other):
        for my, his in zip(self.__parts, other.__parts):
            mynum = isinstance(my, int)
            hisnum = isinstance(his, int)
            if mynum != hisnum:
                return mynum #numbers are less than strings
            if my != his:
                return my < his
        return len(self.__parts) < len(other.__parts)
    
    def __gt__(self, other):
        for my, his in zip(self.__parts, other.__parts):
            mynum = isinstance(my, int)
            hisnum = isinstance(his, int)
            if mynum != hisnum:
                return hisnum #numbers are less than strings
            if my != his:
                return my > his
        return len(self.__parts) > len(other.__parts)
    
    def __le__(self, other):
        return not self.__gt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)
    
# Extracted from hashlib.file_digest added in Python 3.11 
def _hash_stream(fileobj, digest_objs, bufsize):
    """Update one or more digest objects from a file-like object."""
    if hasattr(fileobj, "getbuffer"):
        # io.BytesIO — zero-copy buffer, share across all hashers
        buf = fileobj.getbuffer()
        for d in digest_objs:
            d.update(buf)
        return

    # Only binary files implement readinto().
    if not (
        hasattr(fileobj, "readinto")
        and hasattr(fileobj, "readable")
        and fileobj.readable()
    ):
        raise ValueError(
            f"'{fileobj!r}' is not a file-like object in binary reading mode."
        )

    # binary file, socket.SocketIO object
    # Note: socket I/O uses different syscalls than file I/O.
    buf = bytearray(bufsize)
    view = memoryview(buf)
    while True:
        size = fileobj.readinto(buf)
        if size == 0:
            break  # EOF
        chunk = view[:size]
        for d in digest_objs:
            d.update(chunk)

# Adapted from hashlib.file_digest added in Python 3.11 
def file_digest(fileobj, digest, /, *, _bufsize=2**18):
    """Hash the contents of a file-like object. Returns a digest object.

    *fileobj* must be a file-like object opened for reading in binary mode.
    It accepts file objects from open(), io.BytesIO(), and SocketIO objects.
    The function may bypass Python's I/O and use the file descriptor *fileno*
    directly.

    *digest* must either be a hash algorithm name as a *str*, a hash
    constructor, or a callable that returns a hash object.
    """
    # On Linux we could use AF_ALG sockets and sendfile() to achieve zero-copy
    # hashing with hardware acceleration.
    if isinstance(digest, str):
        digests = (hashlib.new(digest), )
    else:
        digests = (digest(), )

    _hash_stream(fileobj, digests, _bufsize)
    return digests[0]

def file_multi_digest(fileobj, digest, /, *, _bufsize=2**18):
    """Hash the contents of a file-like object. Returns a digest object.

    *fileobj* must be a file-like object opened for reading in binary mode.
    It accepts file objects from open(), io.BytesIO(), and SocketIO objects.
    The function may bypass Python's I/O and use the file descriptor *fileno*
    directly.

    *digest* must either be a tuple/list of any of
     - a hash algorithm name as a *str*
     - a hash constructor
     - a callable that returns a hash object
    """
    if isinstance(digest, tuple) or isinstance(digest, list):
        digests = tuple(hashlib.new(d) if isinstance(d, str) else d() for d in digest)
    else:
        digests = (digest(), )

    _hash_stream(fileobj, digests, _bufsize)
    return digests
    

# Copy of ET.indent added in Python 3.9
def indent_tree(tree, space="  ", level=0):
    """Indent an XML document by inserting newlines and indentation space
    after elements.

    *tree* is the ElementTree or Element to modify.  The (root) element
    itself will not be changed, but the tail text of all elements in its
    subtree will be adapted.

    *space* is the whitespace to insert for each indentation level, two
    space characters by default.

    *level* is the initial indentation level. Setting this to a higher
    value than 0 can be used for indenting subtrees that are more deeply
    nested inside of a document.
    """
    if isinstance(tree, ET.ElementTree):
        tree = tree.getroot()
    if level < 0:
        raise ValueError(f"Initial indentation level must be >= 0, got {level}")
    if not len(tree): # pylint: disable=use-implicit-booleaness-not-len
        return

    # Reduce the memory consumption by reusing indentation strings.
    indentations = ["\n" + level * space]

    def _indent_children(elem, level):
        # Start a new indentation level for the first child.
        child_level = level + 1
        try:
            child_indentation = indentations[child_level]
        except IndexError:
            child_indentation = indentations[level] + space
            indentations.append(child_indentation)

        if not elem.text or not elem.text.strip():
            elem.text = child_indentation

        child = None
        for child in elem:
            if len(child):
                _indent_children(child, child_level)
            if not child.tail or not child.tail.strip():
                child.tail = child_indentation

        # Dedent after the last child by overwriting the previous indentation.
        if child is not None and not child.tail.strip():
            child.tail = indentations[level]

    _indent_children(tree, 0)

class ImmutableDict(Mapping[Key, Val]):
    """A dictionary that cannot be modified"""

    def __init__(self, data: Dict[Key, Val]):
        self.__data = data

    def __getitem__(self, key: Key) -> Val: 
        return self.__data[key]

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)
    
    def items(self):
        return self.__data.items()
    
    def values(self):
        return self.__data.values()
    

class NoPublicConstructor(type):
    """Metaclass that ensures a private constructor

    If a class uses this metaclass like this:

        class SomeClass(metaclass=NoPublicConstructor):
            pass

    If you try to instantiate your class (`SomeClass()`),
    a `TypeError` will be thrown.
    """

    def __call__(cls, *args, **kwargs):
        raise TypeError(
            f"{cls.__module__}.{cls.__qualname__} has no public constructor"
        )

    def _create(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        return super().__call__(*args, **kwargs) 
