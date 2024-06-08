# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""All things related to PGP signing"""

from __future__ import annotations

import subprocess
from pathlib import Path
from os import PathLike
from typing import Optional

from .util import path_from_pathlike

class PgpSigner:
    """Implementation of PGP signing

    Many repository formats rely on PGP signing and use this class for it.

    This class simply delegates signing to `gpg` executable that needs to be present on $PATH.
    Unfortunately, currently there seems to be no good way to perform PGP signing in "pure Python".

    You are required to supply key name and password for signing. Signing is done non-interactively without any
    user prompts.
    """
    def __init__(self, *, key_name: str, key_pwd: str, homedir: Optional[str | PathLike[str]] = None):
        """Constructor for PgpSigner class

        Args:
            key_name: name or identifier of the key to use
            key_pwd: password of the key
            homedir: GPG home directory. If not specified the gpg defaults are used (including
                honoring GNUPGHOME environment variable)
        """
        self.__homedir = path_from_pathlike(homedir) if homedir is not None else None
        self.__key_name = key_name
        self.__key_pwd = key_pwd
        
    def sign_external(self, path: Path, sig_path: Path):
        """Signs a given file producing text (aka "armored") signature in a separate file

        Args:
            path: file to sign
            sig_path: path to write the signature to
        """
        command = ['gpg', '--batch', '--quiet', '--pinentry-mode=loopback']
        if self.__homedir is not None:
            command += ['--homedir', self.__homedir]
        command += [
            '--armor', '--detach-sign', '--sign',
            '--default-key', self.__key_name,
            '--passphrase', self.__key_pwd,
            '--digest-algo', 'sha512',
            '-o', sig_path, path
        ]
        subprocess.run(command, check=True)
        
    def binary_sign_external(self, path: Path, sig_path: Path):
        """Signs a given file producing binary signature in a separate file

        Args:
            path: file to sign
            sig_path: path to write the signature to
        """
        command = ['gpg', '--batch', '--quiet', '--pinentry-mode=loopback']
        if self.__homedir is not None:
            command += ['--homedir', self.__homedir]
        command += [
            '--detach-sign', '--sign', 
            '--default-key', self.__key_name,
            '--passphrase', self.__key_pwd,
            '--digest-algo', 'sha512',
            '-o', sig_path, path
        ]
        subprocess.run(command, check=True)
        
    def sign_inline(self, path: Path, out_path: Path):
        """Adds a signature to a given text file

        Args:
            path: file to sign
            out_path: path to write the signed content to
        """
        command = ['gpg', '--batch', '--quiet', '--pinentry-mode=loopback']
        if self.__homedir is not None:
            command += ['--homedir', self.__homedir]
        command += [
            '--armor', '--detach-sign', '--sign', '--clearsign', 
            '--default-key', self.__key_name,
            '--passphrase', self.__key_pwd,
            '--digest-algo', 'sha512',
            '-o', out_path, path
        ]
        subprocess.run(command, check=True)
        
    def export_public_key(self, path: Path):
        """Utility method to export the public key of the signing key into a file
        Args:
            path: path of the file to write the public key to
        """
        command = ['gpg', '--batch', '--quiet']
        if self.__homedir is not None:
            command += ['--homedir', self.__homedir]
        command += [
            '--output', path, 
            '--armor', '--export', self.__key_name
        ]
        subprocess.run(command, check=True)

