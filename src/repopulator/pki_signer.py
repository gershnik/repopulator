# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""All things related to PKI signing"""

from __future__ import annotations

import hashlib

from pathlib import Path
from os import PathLike

from cryptography.hazmat.backends.openssl.backend import backend as openssl_backend
from cryptography.hazmat.primitives import hashes as crypto_hashes
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import padding as crypto_padding, rsa, ec, ed25519

from typing import Optional

from .util import file_digest


class PkiSigner:
    """Implementation of private key based signing

    Many repository formats rely on private key signing and use this class for it.

    The supplied key needs to be in PEM format. Its cryptographic type needs to be appropriate for the repository
    that it will be used for.
    """

    def __init__(self, priv_key_path: str | PathLike[str], priv_key_passwd: Optional[str]):
        """Constructor for PkiSigner class

        The private key file is read once during the construction and not used again
        Args:
            priv_key_path: path to the private key file. The file must be in PEM format.
            priv_key_passwd: password for the key if it requires one.
        """
        ver = openssl_backend.openssl_version_number()
        if ver < 0x30000000:
            raise RuntimeError(f'Unsupported OpenSSL version: 0x{ver:08x}, must be above 0x30000000')
        with open(priv_key_path, 'rb') as key_file:
            key = key_file.read()
            pwd = priv_key_passwd.encode() if priv_key_passwd is not None else None
            self.__key = crypto_serialization.load_pem_private_key(key, pwd, openssl_backend)
            
        
    def get_free_bsd_signature(self, path: Path):
        """Generate file signature in a format required by FreeBSD repositories

        Private key type must be one of: rsa, ecdsa or eddsa
        Args:
            path: path of the file to sign
        Returns:
            Signature as a `bytes` object
        """
        with open(path, 'rb') as data_file:
            if isinstance(self.__key, rsa.RSAPrivateKey):
                digest = file_digest(data_file, hashlib.sha256).hexdigest()
            else:
                digest = file_digest(data_file, hashlib.blake2b).hexdigest()

        if isinstance(self.__key, rsa.RSAPrivateKey):
            padding = crypto_padding.PKCS1v15()
            hash_algo = crypto_hashes.SHA256()
            signature = self.__key.sign(digest.encode(), padding, hash_algo)
        elif isinstance(self.__key, ec.EllipticCurvePrivateKey):
            algo = ec.ECDSA(crypto_hashes.SHA256())
            signature = self.__key.sign(digest.encode(), algo)
            signature = b'$PKGSIGN:ecdsa' + signature
        elif isinstance(self.__key, ed25519.Ed25519PrivateKey):
            signature = self.__key.sign(digest.encode())
            signature = b'$PKGSIGN:eddsa' + signature
        else:
            raise ValueError('The private key type is not currently supported for BSD signatures')
        
        return signature

    def get_alpine_signature(self, path: Path):
        """Generate file signature in a format required by Alpine apk repositories

        Only rsa keys are currently supported

        Args:
            path: path of the file to sign
        Returns:
            Signature as a `bytes` object
        """
        if not isinstance(self.__key, rsa.RSAPrivateKey):
            raise ValueError('The private key type is not currently supported for Alpine signatures')

        data = path.read_bytes()

        padding = crypto_padding.PKCS1v15()
        hash_algo = crypto_hashes.SHA1()
        signature = self.__key.sign(data, padding, hash_algo)
        return signature
