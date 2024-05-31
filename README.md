

# repolulator

A portable Python library to generate binary software repositories (APT, YUM/DNF etc.) 

[![License](https://img.shields.io/badge/license-BSD-brightgreen.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Language](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org)
[![python](https://img.shields.io/badge/python->=3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)

## Purpose

Ever needed to build an APT package repository on Fedora? Or perhaps a DNF repository on Debian? How about FreeBSD repository on Windows or Mac? This library allows you to do all these things and more.

All binary package repositories have their own tools that usually range from being "non-portable" to "portable with lots of effort to limited platforms only". On the other hand it is often convenient to build software packages in a Map/Reduce fashion where a single host collects multiple packages built for different platforms to produce binary repositories. Such host will necessarily need to be able to build repositories for "foreign" packages. This library is an attempt to enable such scenario.

## Requirements

* Python >= 3.8
* If you plan to build repositories that require GPG signing `gpg` command needs to be available in PATH

## Supported repository formats

* APT
* RPM
* FreeBSD pkg

## Installing

```bash
pip install repopulator
```

### Sample Usage

#### APT

```python
from repopulator import AptRepo, PgpSigner
from pathlib import Path

repo = AptRepo()

package1 = repo.addPackage(Path('/path/to/awesome_3.14_amd64.deb'))
package2 = repo.addPackage(Path('/path/to/awesome_3.14_arm64.deb'))

dist = repo.addDistribution('jammy', 
                            origin='my packages', 
                            label='my apt repo', 
                            suite='jammy', 
                            version='1.2', 
                            description='my awesome repo')

dist.addPackage(component='main', package=package1)
dist.addPackage(component='main', package=package2)

signer = PgpSigner(Path.home() / '.gnupg', 'name_of_key_to_use', 'password_of_that_key')

repo.export(Path('/path/of/new/repo'), signer)

```

#### YUM/DNF

```python
from repopulator import RpmRepo, PgpSigner
from pathlib import Path

repo = RpmRepo()
repo.addPackage(Path('/path/to/awesome-3.14-1.el9.x86_64.rpm'))
repo.addPackage(Path('/path/to/awesome-3.14-1.el9.aarch64.rpm'))

signer = PgpSigner(Path.home() / '.gnupg', 'name_of_key_to_use', 'password_of_that_key')

repo.export(Path('/path/of/new/repo'), signer)

```

#### FreeBSD pkg

```python
from repopulator import FreeBSDRepo, PkiSigner
from pathlib import Path

repo = FreeBSDRepo()
repo.addPackage(Path('/path/to/awesome-3.14.pkg'))
repo.addPackage(Path('/path/to/another-1.2.pkg'))

signer = PkiSigner(Path('/path/to/private/key'), 'password_or_None')

repo.export(Path('/path/of/new/repo'), signer)

```

