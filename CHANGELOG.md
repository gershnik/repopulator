# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

## Unreleased

### Fixed

- Incorrect deduplication of multiple APT packages with disjoint architectures
- RPM "other" metadata in `repomd.xml` now uses correct format and is no longer ignored by YUM/DNF
- FreeBSD packages using zstd compression can now be imported on Python < 3.14
- VersionKey `__hash__` now actually works.
- Exception when RPM "serial" key is an integer.
- Adding an older version of a package to a Pacman repo now properly reports an exception instead of 
  silently doing nothing.
- `AptRepo` now leaves any non `*.deb` files alone in a destination pool (as was promised by the docs).
- `gpg` passphrase is no longer passed on the command line. 
- Dotless signature files are now handled correctly on the command line.
- Typos and grammar in documentation.
- Tests now work again.

### Added

- `RpmVersion` now has a decent `__repr__`.
- `PacmanRepo` now accepts string or PathLike destination paths like all other repos.
- Performance improvements for APT and RPM repository generation

### Changed

- PyPy 3.9 and 3.10 are no longer supported (due to dependencies no longer supporting them)

## [1.6] - 2025-05-13

### Changed
- Bumping minimum supported Python to 3.9
- Bumping required setuptools version to 77.0.3 to support PEP 639

## [1.5] - 2025-05-13

### Changed
- Switched to using official `rpmfile` dependency instead of a bundled one since it now incorporates our fixes.
- Package metadata has been updated to conform to the newest setuptools requirements

## [1.4] - 2024-12-30

### Changed
- Dependencies are now `>=` rather than `~=` to better align with Python libraries best practices.

## [1.3] - 2024-10-04

### Fixed
- Incorrect file paths in APT repos.

## [1.2] - 2024-09-10

### Changed
- Updated dependencies. Notably `cryptography` dependency is now ~=43.0.1

## [1.1] - 2024-06-21

### Added
- Command-line interface. Invoke with `repopulator` (or `python3 -m repopulator`) 

### Changed
- AptRepo.add_distribution informational fields arguments are now optional rather than required.

## [1.0] - 2024-06-08

### Added
- CRUD for all repo-related objects

### Fixed
- `PgpSigner` now respects home directory parameter
- Project is now Stable

## [0.7] - 2024-06-05

### Changed
- First beta version

## [0.6] - 2024-06-05

### Added
- Documentation for all of public API

### Changed
- Naming convention changed to conform to PEP standards

## [0.5] - 2024-06-05

### Fixed
- Broken APT `Package.gz` generation

## [0.4] - 2024-06-04

### Added
- Alpine apk repositories are now supported

## [0.3] - 2024-06-02

### Added
- Pacman repositories are now supported

## [0.2] - 2024-06-01

### Added
- Initial version

[0.2]: https://github.com/gershnik/repopulator/releases/0.2
[0.3]: https://github.com/gershnik/repopulator/releases/0.3
[0.4]: https://github.com/gershnik/repopulator/releases/0.4
[0.5]: https://github.com/gershnik/repopulator/releases/0.5
[0.6]: https://github.com/gershnik/repopulator/releases/0.6
[0.7]: https://github.com/gershnik/repopulator/releases/0.7
[1.0]: https://github.com/gershnik/repopulator/releases/1.0
[1.1]: https://github.com/gershnik/repopulator/releases/1.1
[1.2]: https://github.com/gershnik/repopulator/releases/1.2
[1.3]: https://github.com/gershnik/repopulator/releases/1.3
[1.4]: https://github.com/gershnik/repopulator/releases/1.4
[1.5]: https://github.com/gershnik/repopulator/releases/1.5
[1.6]: https://github.com/gershnik/repopulator/releases/1.6
