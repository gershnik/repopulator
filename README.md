

# repolulator

[![License](https://img.shields.io/badge/license-BSD-brightgreen.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Language](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org)
[![python](https://img.shields.io/badge/python->=3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![pypi](https://img.shields.io/pypi/v/repopulator)](https://pypi.org/project/repopulator)

A portable Python library to generate binary software repositories

## Purpose

Ever needed to build an APT package repository on Fedora? Or perhaps a DNF repository on Debian? How about FreeBSD repository on Windows or Mac? This library allows you to do all these things and more. And yes, you can do it even on Windows if you are so inclined for some reason.

All binary package repositories have their own tools that usually range from being "non-portable" to "portable with lots of effort to limited platforms only". On the other hand it is often convenient to build software packages in a Map/Reduce fashion where a single host collects multiple packages built for different platforms to produce binary repositories. Such host will necessarily need to be able to build repositories for "foreign" packages. This library is an attempt to enable such scenario. It provides both programmatic and command-line access.

## Requirements

* Python >= 3.8
* If you plan to build repositories that require GPG signing `gpg` command needs to be available in PATH
* If you plan to build repositories that require private key signing OpenSSL > 3.0 libraries need to be available on your platform

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

## Documentation

Documentation for API and command-line syntax is available at https://gershnik.github.io/repopulator/

## Examples

### APT

#### Programmatic

```python
from repopulator import AptRepo, PgpSigner

repo = AptRepo()

package1 = repo.add_package('/path/to/awesome_3.14_amd64.deb')
package2 = repo.add_package('/path/to/awesome_3.14_arm64.deb')

dist = repo.add_distribution('jammy')

repo.assign_package(package1, dist, component='main')
repo.assign_package(package2, dist, component='main')

signer = PgpSigner('name_of_key_to_use', 'password_of_that_key')

repo.export('/path/of/new/repo', signer)

```

#### Command-line

```bash
repopulator apt -o /path/of/new/repo -k name_of_key_to_use -w password_of_that_key \
  -d jammy -c main \
  -p /path/to/awesome_3.14_amd64.deb /path/to/awesome_3.14_arm64.deb
```

### RPM

#### Programmatic

```python
from repopulator import RpmRepo, PgpSigner

repo = RpmRepo()
repo.add_package('/path/to/awesome-3.14-1.el9.x86_64.rpm')
repo.add_package('/path/to/awesome-3.14-1.el9.aarch64.rpm')

signer = PgpSigner('name_of_key_to_use', 'password_of_that_key')

repo.export('/path/of/new/repo', signer)

```

#### Command-line

```bash
repopulator rpm -o /path/of/new/repo -k name_of_key_to_use -w password_of_that_key \
  -p /path/to/awesome-3.14-1.el9.x86_64.rpm /path/to/awesome-3.14-1.el9.aarch64.rpm
```

### Pacman

#### Programmatic

```python
from repopulator import PacmanRepo, PgpSigner

repo = PacmanRepo('myrepo')
repo.add_package('/path/to/awesome-3.14-1-x86_64.pkg.tar.zst')
repo.add_package('/path/to/another-1.2-1-x86_64.pkg.tar.zst')

signer = PgpSigner('name_of_key_to_use', 'password_of_that_key')

repo.export('/path/of/new/repo', signer)

```

#### Command-line

```bash
repopulator pacman -o /path/of/new/repo -k name_of_key_to_use -w password_of_that_key \
    -n myrepo -p /path/to/awesome-3.14-1-x86_64.pkg.tar.zst /path/to/another-1.2-1-x86_64.pkg.tar.zst
```

### Alpine apk

#### Programmatic

```python
from repopulator import AlpineRepo, PkiSigner

repo = AlpineRepo('my repo description')
repo.add_package('/path/to/awesome-3.14-r0.apk')
repo.add_package('/path/to/another-1.23-r0.apk')

signer = PkiSigner('/path/to/private/key', 'password_or_None')

# Unlike `pkg` tool we do not parse signer name out of private key filename
# so you can name your key files whatever you wish
repo.export('/path/of/new/repo', signer, signer_name = 'mymail@mydomain.com-1234abcd')

```

#### Command-line

```bash
repopulator alpine -o /path/of/new/repo -d 'my repo description' \
  -k /path/to/private/key.rsa -w password_of_that_key \
  -s 'mymail@mydomain.com-1234abcd' \
  -p /path/to/awesome-3.14-r0.apk /path/to/another-1.23-r0.apk
```

### FreeBSD pkg

#### Programmatic

```python
from repopulator import FreeBSDRepo, PkiSigner

repo = FreeBSDRepo()
repo.add_package('/path/to/awesome-3.14.pkg')
repo.add_package('/path/to/another-1.2.pkg')

signer = PkiSigner('/path/to/private/key', 'password_or_None')

repo.export('/path/of/new/repo', signer)

```

#### Command-line

```bash
repopulator freebsd -o /path/of/new/repo \
  -k /path/to/private/key -w password_of_that_key \
  -p /path/to/awesome-3.14.pkg /path/to/another-1.2.pkg
```

