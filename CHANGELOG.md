# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

## Unreleased

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
