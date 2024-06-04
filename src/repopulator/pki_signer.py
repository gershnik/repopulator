# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

import hashlib

from pathlib import Path

from cryptography.hazmat.backends.openssl.backend import backend as openssl_backend
from cryptography.hazmat.primitives import hashes as crypto_hashes
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import padding as crypto_padding, rsa, ec, ed25519

from typing import Optional

from .util import file_digest


class PkiSigner:
    def __init__(self, privKeyPath: Path, privKeyPasswd: Optional[str]):
        ver = openssl_backend.openssl_version_number()
        if ver < 0x30000000:
            raise Exception(f'Unsupported OpenSSL version: 0x{ver:08x}, must be above 0x30000000')
        with open(privKeyPath, 'rb') as keyFile:
            key = keyFile.read()
            pwd = privKeyPasswd.encode() if privKeyPasswd is not None else None
            self.__key = crypto_serialization.load_pem_private_key(key, pwd, openssl_backend)
            
        
    def getFreeBSDSignature(self, path: Path):
        with open(path, 'rb') as dataFile:
            if isinstance(self.__key, rsa.RSAPrivateKey):
                digest = file_digest(dataFile, hashlib.sha256).hexdigest()
            else:
                digest = file_digest(dataFile, hashlib.blake2b).hexdigest()

        if isinstance(self.__key, rsa.RSAPrivateKey):
            padding = crypto_padding.PKCS1v15()
            hashVal = crypto_hashes.SHA256()
            signature = self.__key.sign(digest.encode(), padding, hashVal)
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

    def getAlpineSignature(self, path: Path):
        if not isinstance(self.__key, rsa.RSAPrivateKey):
            raise Exception('The private key type is not currently supported for Alpine signatures')

        data = path.read_bytes()

        padding = crypto_padding.PKCS1v15()
        hashVal = crypto_hashes.SHA1()
        signature = self.__key.sign(data, padding, hashVal)
        return signature
                    