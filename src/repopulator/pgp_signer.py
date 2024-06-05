# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

import subprocess
from pathlib import Path

class PgpSigner:
    """Implementation of PGP signing

    Many repository formats rely on PGP signing and use this class for it.

    This class simply delegates signing to `gpg` executable that needs to be present on $PATH.
    Unfortunately, currently there seems to be no good way to perform PGP signing in "pure Python".

    You are required to supply key name and password for signing. Signing is done non-interactively without any
    user prompts.
    """
    def __init__(self, homedir: Path, key_name: str, key_pwd: str):
        """Constructor for PgpSigner class

        Args:
            homedir: GPG home directory. This is normally Path.home() / '.gpg' but can be set to anything for
                custom configuration
            key_name: name or identifier of the key to use
            key_pwd: password of the key
        """
        self.__homedir = homedir
        self.__keyName = key_name
        self.__keyPwd = key_pwd
        
    def sign_external(self, path: Path, sig_path: Path):
        """Signs a given file producing text (aka "armored") signature in a separate file

        Args:
            path: file to sign
            sig_path: path to write the signature to
        """
        subprocess.run(['gpg', '--batch', '--quiet', '--pinentry-mode=loopback',
                        '--armor', '--detach-sign', '--sign',
                        '--default-key', self.__keyName,
                        '--passphrase', self.__keyPwd,
                        '--digest-algo', 'sha512',
                        '-o', sig_path, path
                        ], check=True)
        
    def binary_sign_external(self, path: Path, sig_path: Path):
        """Signs a given file producing binary signature in a separate file

        Args:
            path: file to sign
            sig_path: path to write the signature to
        """
        subprocess.run(['gpg', '--batch', '--quiet', '--pinentry-mode=loopback',
                        '--detach-sign', '--sign', 
                        '--default-key', self.__keyName,
                        '--passphrase', self.__keyPwd,
                        '--digest-algo', 'sha512',
                        '-o', sig_path, path
                        ], check=True)
        
    def sign_inline(self, path: Path, out_path: Path):
        """Adds a signature to a given text file

        Args:
            path: file to sign
            out_path: path to write the signed content to
        """
        subprocess.run(['gpg', '--batch', '--quiet', '--pinentry-mode=loopback', 
                        '--armor', '--detach-sign', '--sign', '--clearsign', 
                        '--default-key', self.__keyName,
                        '--passphrase', self.__keyPwd,
                        '--digest-algo', 'sha512',
                        '-o', out_path, path
                        ], check=True)
        
    def export_public_key(self, path: Path):
        """Utility method to export the public key of the signing key into a file
        Args:
            path: path of the file to write the public key to
        """
        subprocess.run(['gpg', '--batch', '--quiet', '--output', path, 
                        '--armor', '--export', self.__keyName
                        ], check=True)

    