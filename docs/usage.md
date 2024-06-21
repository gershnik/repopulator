# Usage

The basic outline of the usage is the same for all repository types:

- Create the repository object
- Add packages to it. These must be files somewhere on your filesystem *which is not their final destination*
- Some repositories like APT have additional subdivisions (distributions for APT). If so you need to create them and assign packages added to repository to them
- Export the repository to the destination folder. This overwrites any repository already there (but not any extra files you might have). 

That's all there is to it. Note that there is no ability to "load" existing repositories and change them. This is deliberate. If you want to do incremental repository maintenance it is far easier to keep necessary info yourself in your own format than to parse it out of various repositories. 

Currently repositories are required to be signed and you need to provide signing info for export (see examples below). This requirement might be relaxed in future versions.

## APT

```python
from repopulator import AptRepo, PgpSigner

repo = AptRepo()

package1 = repo.add_package('/path/to/awesome_3.14_amd64.deb')
package2 = repo.add_package('/path/to/awesome_3.14_arm64.deb')

# The keyword arguments are all optional
dist = repo.add_distribution('jammy', 
                             origin='my packages', 
                             label='my apt repo', 
                             suite='jammy', 
                             codename='jammy', 
                             version='1.2', 
                             description='my awesome repo')

repo.assign_package(package1, dist, component='main')
repo.assign_package(package2, dist, component='main')

signer = PgpSigner('name_of_key_to_use', 'password_of_that_key')

repo.export('/path/of/new/repo', signer)

```

## RPM

```python
from repopulator import RpmRepo, PgpSigner

repo = RpmRepo()
repo.add_package('/path/to/awesome-3.14-1.el9.x86_64.rpm')
repo.add_package('/path/to/awesome-3.14-1.el9.aarch64.rpm')

signer = PgpSigner('name_of_key_to_use', 'password_of_that_key')

repo.export('/path/of/new/repo', signer)

```

## Pacman

```python
from repopulator import PacmanRepo, PgpSigner

repo = PacmanRepo('myrepo')
# if .sig file is present next to the .zst file it will be used for signature
# otherwise new signature will be generated at export time
repo.add_package('/path/to/awesome-3.14-1-x86_64.pkg.tar.zst')
repo.add_package('/path/to/another-1.2-1-x86_64.pkg.tar.zst')

signer = PgpSigner('name_of_key_to_use', 'password_of_that_key')

repo.export('/path/of/new/repo', signer)

```

## Alpine apk

```python
from repopulator import AlpineRepo, PkiSigner

repo = AlpineRepo('my repo description')
repo.add_package('/path/to/awesome-3.14-r0.apk')
repo.add_package('/path/to/another-1.23-r0.apk')

# Every package in a repo must belong to a specific architecture
# By default, the architecture is taken from the package. Some
# packages like for example -doc- ones are 'noarch' - e.g. 
# architecture independent. For these you need to use force_arch 
# argument.
repo.add_package('/path/to/another-doc-1.23-r0.apk', force_arch='x86_64')

signer = PkiSigner('/path/to/private/key', 'password_or_None')

# Unlike `pkg` tool we do not parse signer name out of the private key filename
# so you can name your key files whatever you wish
repo.export('/path/of/new/repo', signer, signer_name = 'mymail@mydomain.com-1234abcd')

```

## FreeBSD pkg

```python
from repopulator import FreeBSDRepo, PkiSigner

repo = FreeBSDRepo()
repo.add_package('/path/to/awesome-3.14.pkg')
repo.add_package('/path/to/another-1.2.pkg')

signer = PkiSigner('/path/to/private/key', 'password_or_None')

repo.export('/path/of/new/repo', signer)

```
