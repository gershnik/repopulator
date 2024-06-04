

# repolulator

[![License](https://img.shields.io/badge/license-BSD-brightgreen.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Language](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org)
[![python](https://img.shields.io/badge/python->=3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![pypi](https://img.shields.io/pypi/v/repopulator)](https://pypi.org/project/repopulator)

A portable Python library to generate binary software repositories (APT, YUM/DNF, Pacman etc.) 

## Purpose

Ever needed to build an APT package repository on Fedora? Or perhaps a DNF repository on Debian? How about FreeBSD repository on Windows or Mac? This library allows you to do all these things and more. And yes, you can do it even on Windows if you are so inclined for some reason.

All binary package repositories have their own tools that usually range from being "non-portable" to "portable with lots of effort to limited platforms only". On the other hand it is often convenient to build software packages in a Map/Reduce fashion where a single host collects multiple packages built for different platforms to produce binary repositories. Such host will necessarily need to be able to build repositories for "foreign" packages. This library is an attempt to enable such scenario.

## Requirements

* Python >= 3.8
* If you plan to build repositories that require GPG signing `gpg` command needs to be available in PATH

## Supported repository formats

* APT
* RPM
* Pacman
* Alpine apk
* FreeBSD pkg

## Installing

```bash
pip install repopulator
```

### Sample Usage

The basic outline of the usage is the same for all repository types:
- Create the repository object
- Add packages to it. These must be files somewhere on your filesystem *which is not their final destination*
- Some repositories like APT have additional subdivisions (distributions for APT). If so you need to create them and assign packages added to repository to them
- Export the repository to the destination folder. This overwrites any repository already there (but not any extra files you might have). 

That's all there is to it. Note that there is no ability to "load" existing repositories and change them. This is deliberate. If you want to do incremental repository maintenance it is far easier to keep necessary info yourself in your own format than to parse it out of various repositories. 

Currently repositories are required to be signed and you need to provide signing info for export (see examples below). This requirement might be relaxed in future versions.

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

#### Pacman

```python
from repopulator import PacmanRepo, PgpSigner
from pathlib import Path

repo = PacmanRepo('myrepo')
# if .sig file is present next to the .zst file it will be used for signature
# otherwise new signature will be generated at export time
repo.addPackage(Path('/path/to/awesome-3.14-1-x86_64.pkg.tar.zst'))

signer = PgpSigner(Path.home() / '.gnupg', 'name_of_key_to_use', 'password_of_that_key')

repo.export(Path('/path/of/new/repo'), signer)

```

#### Alpine apk

```python
from repopulator import PacmanRepo, PkiSigner
from pathlib import Path

repo = PacmanRepo('my repo description')
epo.addPackage(Path('/path/to/awesome-3.14-r0.apk'))

signer = PkiSigner(Path('/path/to/private/key'), 'password_or_None')

# The last argument is the 'name' of the signer to use
# Unlike `pkg` tool we do not parse it out of private key filename
# and do not require you to name key files in certain way
repo.export(Path('/path/of/new/repo'), signer, 'mymail@mydomain.com-1234abcd')

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

