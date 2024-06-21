# Command-Line Interface

## General

The `repopulator` module provides a simple command-line interface to create repositories.

You can invoke the command-line either via a script
```bash
$ repopulator
```
or as a module
```bash
$ python3 -m repopulator
```

The general form of the command line is:

```bash
$ repopulator TYPE -o DEST [options...] -p package1 package2 ....
```

where `TYPE` is one of: `alpine`, `apt`, `freebsd`, `pacman`, `rpm` and `DEST` is the destination directory for the repository.

You can obtain overall help by using
```bash
$ repopulator -h/--help
```

and a help about available options for each repository via:
```bash
$ repopulator TYPE -h/--help
```

Options and their effect for each repository type are described below

## Alpine

The general command-line form for Alpine pkg repository is:

```bash
$ repopulator alpine -o DEST -d DESC -k KEY_PATH [-w KEY_PASSWORD] [-s SIGNER] \
     -p package1 package2 ... \
     -a ARCH1 -p package3 package4 ... \
     -a ARCH2 -p package5 package6 ...

```

Where:

`-d DESC`, `--desc DESC`
: The repository description

`-k KEY_PATH`, `--key KEY_PATH`
: The path to private key for signing. If `-s/--signer` option is not supplied the stem of the private key filename is used as the name. So for example a key `someone@someorg.com-123456.rsa` will result in `someone@someorg.com-123456` being used as a signer name.

`-w KEY_PASSWORD`, `--password KEY_PASSWORD`
: The password for the private key, if needed

`-s SIGNER`, `--signer SIGNER`
: The signer name that overrides automatic deduction from the key filename described above

`-a ARCH`, `--arch ARCH`
: Forces the architecture of the _following_ packages to be `ARCH`. 

`-p path ...`, `--package path...`
: `.apk` packages to add

By default, internal architecture of the package is used to decide under which architecture to register it in the repo. 
Some packages (such as `-doc-`, `-openrc-` etc.) do not have specific architecture and are marked as `noarch`. All Alpine packages in a repo must belong to some architecture so you need to use `-a ARCH` with them. 

If you wish to "stop" the latest `-a ARCH` effect and revert to using architecture of the package use `-a` without an argument.

## APT

The general command-line form for APT repository is:

```bash
$ repopulator apt -o DEST -k KEY_NAME -w KEY_PASSWORD \
    -d DISTRO1 \
      [--origin ORIGIN] [--label LABEL] [--suite SUITE] \
        [--codename CODENAME] [--version VERSION] [--desc DESC] \
      [-c COMPONENT1] \
          -p package1 package2 ... \
      [-c COMPONENT2] \
          -p package3 package4 ... \
    -d DISTRO2 \
    ...
```

Where:

`-k KEY_NAME`, `--key KEY_NAME`
: Name or ID of the GPG key for signing

`-w KEY_PASSWORD`, `--password KEY_PASSWORD`
: GPG key password

`-d DISTRO`, `--distro DISTRO`
: Starts a new distribution named `DISTRO` (e.g. `jammy` or `focal`). All subsequent arguments refer to this distribution until the next `-d/--distro` argument. The distribution name can be a path like `stable/updates`

`--origin ORIGIN`
: Optional `Origin` field for the distribution. See https://wiki.debian.org/DebianRepository/Format#Origin

`--label LABEL`
: Optional `Label` field for the distribution. See https://wiki.debian.org/DebianRepository/Format#Label

`--suite SUITE`
: Optional `Suite` field for the distribution. See https://wiki.debian.org/DebianRepository/Format#Suite. If omitted defaults to the last component of distribution path.

`--codename CODENAME`
: Optional `Codename` field for the distribution. See https://wiki.debian.org/DebianRepository/Format#Codename. If omitted defaults to the last component of distribution path.

`--version VERSION`
: Optional `Version` field for the distribution. See https://wiki.debian.org/DebianRepository/Format#Version. If omitted defaults to the last component of distribution path.

`--desc DESC`
: Optional `Description` field for the distribution. See https://wiki.debian.org/DebianRepository/Format#Description. If omitted defaults to the last component of distribution path.

`-c COMPONENT`, `--comp COMPONENT`
: Optional component of the _following_ packages. If not specified or component name is omitted defaults to `main`. You can specify multiple components for a distribution. 

`-p path ...`, `--package path...`
: `.deb` (or `.udeb`) packages to add to the current distribution and component

## FreeBSD

The general command-line form for FreeBSD repository is:

```bash
$ repopulator freebsd -o DEST -k KEY_PATH [-w KEY_PASSWORD] \
     -p package1 package2 ... 
```

Where:

`-k KEY_PATH`, `--key KEY_PATH`
: The path to private key for signing. 

`-w KEY_PASSWORD`, `--password KEY_PASSWORD`
: The password for the private key, if needed

`-p path ...`, `--package path...`
: `.pkg` packages to add


## Pacman

The general command-line form for Pacman repository is:

```bash
$ repopulator pacman -o DEST -k KEY_NAME -w KEY_PASSWORD \
    -n name -p package1 package2 ...
```

Where:

`-k KEY_NAME`, `--key KEY_NAME`
: Name or ID of the GPG key for signing

`-w KEY_PASSWORD`, `--password KEY_PASSWORD`
: GPG key password

`-n NAME`, `--name NAME`
: Repository name

`-p path ...`, `--package path...`
: `.zst` packages to add. If a matching .sig file with the same name exists next to the package, it will be automatically used to supply the package signature

## RPM

The general command-line form for Pacman repository is:

```bash
$ repopulator rpm -o DEST -k KEY_NAME -w KEY_PASSWORD \
    -p package1 package2 ...
```

Where:

`-k KEY_NAME`, `--key KEY_NAME`
: Name or ID of the GPG key for signing

`-w KEY_PASSWORD`, `--password KEY_PASSWORD`
: GPG key password

`-p path ...`, `--package path...`
: `.rpm` packages to add. 
