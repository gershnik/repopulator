# repopulator - generate binary software repositories

The `repopulator` module allows you to generate APT, DNF/YUM, YUM/DNF, Pacman etc. binary software repositories.
This is done in a portable fashion without relying on any platform and distribution specific tools.


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


## Reference

::: repopulator
options:
    summary:
    modules: false