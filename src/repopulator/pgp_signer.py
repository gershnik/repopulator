# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

import subprocess
from pathlib import Path

class PgpSigner:
    def __init__(self, homedir: Path, keyName: str, keyPwd: str):
        self.homedir = homedir
        self.keyName = keyName
        self.keyPwd = keyPwd
        
    def signExternal(self, path: Path, sigPath: Path):
        subprocess.run(['gpg', '--batch', '--quiet', '--pinentry-mode=loopback',
                        '--armor', '--detach-sign', '--sign',
                        '--default-key', self.keyName,  
                        '--passphrase', self.keyPwd,
                        '--digest-algo', 'sha512',
                        '-o', sigPath, path
                        ], check=True)
        
    def binarySignExternal(self, path: Path, sigPath: Path):
        subprocess.run(['gpg', '--batch', '--quiet', '--pinentry-mode=loopback',
                        '--detach-sign', '--sign', 
                        '--default-key', self.keyName, 
                        '--passphrase', self.keyPwd,
                        '--digest-algo', 'sha512',
                        '-o', sigPath, path
                        ], check=True)
        
    def signInline(self, path: Path, outPath: Path):
        subprocess.run(['gpg', '--batch', '--quiet', '--pinentry-mode=loopback', 
                        '--armor', '--detach-sign', '--sign', '--clearsign', 
                        '--default-key', self.keyName,
                        '--passphrase', self.keyPwd,
                        '--digest-algo', 'sha512',
                        '-o', outPath, path
                        ], check=True)
        
    def exportPublicKey(self, path: Path):
        subprocess.run(['gpg', '--batch', '--quiet', '--output', path, 
                        '--armor', '--export', self.keyName
                        ], check=True)

    