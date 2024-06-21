# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

# pylint: disable=missing-function-docstring

"""Command line utility"""

from __future__ import annotations

import sys
import argparse

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Sequence, Tuple

from repopulator.alpine import AlpineRepo
from repopulator.apt import AptPackage, AptRepo
from repopulator.freebsd import FreeBSDRepo
from repopulator.pacman import PacmanRepo
from repopulator.rpm import RpmRepo
from repopulator.pgp_signer import PgpSigner
from repopulator.pki_signer import PkiSigner
from repopulator.version import VERSION


class _Handler(metaclass=ABCMeta):
    @abstractmethod
    def add_parser(self, key: str, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]):
        ...

    @abstractmethod
    def handle(self, args: argparse.Namespace) -> int:
        ...


class _AlpineHandler(_Handler):
    class _ExtendPackageAction(argparse._ExtendAction):
        def __call__(self, 
                    parser: argparse.ArgumentParser, 
                    namespace: argparse.Namespace, 
                    values: str | Sequence[Any] | None, 
                    option_string: str | None = None) -> None:
            if isinstance(values, list):
                value = [(x, namespace.arch) for x in values]
            else:
                value = (values, namespace.arch)
            super().__call__(parser, namespace, value, option_string)

    def add_parser(self, key: str, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]):
        parser: argparse.ArgumentParser = subparsers.add_parser(key, description='Create Alpine apk repo')
        
        parser.add_argument('-o', '--output', dest='dest', type=Path, metavar='DEST', required=True,
                            help='output path to export the repository to')
        
        parser.add_argument('-d', '--desc', type=str, dest='desc', required=True,
                            help='repository description')
        parser.add_argument('-k', '--key', type=Path, dest='key_path', metavar='KEY_PATH', required=True,
                            help='path of the private key for signing. If -s/--signer option is not supplied '
                            'the stem of the private key filename is used as the name. '
                            'So for example a key someone@someorg.com-123456.rsa will result in someone@someorg.com-123456 '
                            'being used as a signer name.')
        parser.add_argument('-w', '--password', type=str, dest='key_password', metavar='KEY_PASSWORD',
                            help='private key password')
        parser.add_argument('-s', '--signer', type=str, dest='signer',
                            help='name of the signer. This can be used to override name deduced from the key filename')
        
        parser.add_argument('-a', '--arch', dest='arch', metavar='ARCH', nargs='?', default=None,
                            help='override architecture of subsequent packages. To cancel override use -a/--arch '
                            'with no arguments')
        
        parser.add_argument('-p', '--packages', nargs='+', metavar='PACKAGE', 
                            action=_AlpineHandler._ExtendPackageAction,
                            help='.apk file(s) to add to repository')


    def handle(self, args: argparse.Namespace):
        desc: str = args.desc 
        packages: Sequence[str] = args.packages
        key_path: Path = args.key_path 
        key_password: str | None = args.key_password
        signer_name: str | None = args.signer
        dest: Path = args.dest

        if signer_name is None:
            last_dot_idx = key_path.name.rfind('.')
            if last_dot_idx == 0:
                print('unable to determine signer name from the key, please use --signer option', file=sys.stderr)
                return 1
            signer_name = key_path.name[0:last_dot_idx]    
            
        print(f'Signing as {signer_name}')
        
        repo = AlpineRepo(desc)
        for name, arch in packages:
            if arch is not None:
                print(f'Adding {name} with architecture {arch}')
                repo.add_package(name, force_arch=arch)
            else:
                print(f'Adding {name}')
                repo.add_package(name)
        signer = PkiSigner(key_path, key_password)
        
        repo.export(dest, signer, signer_name)

        return 0


class _FreeBSDHandler(_Handler):
    def add_parser(self, key: str, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]):
        parser: argparse.ArgumentParser = subparsers.add_parser(key, description='Create FreeBSD pkg repo')
        
        parser.add_argument('-o', '--output', dest='dest', type=Path, metavar='DEST', required=True,
                            help='output path to export the repository to')
        parser.add_argument('-k', '--key', type=Path, dest='key_path', metavar='PATH', required=True,
                            help='path of the private key for signing.')
        parser.add_argument('-w', '--password', type=str, dest='key_password', metavar='PASSWORD', 
                            help='private key password')
        parser.add_argument('-p', '--packages', nargs='+', metavar='PACKAGE', action='extend',
                            help='.pkg file(s) to add to repository.')

    def handle(self, args: argparse.Namespace):
        packages: Sequence[str] = args.packages
        key_path: Path = args.key_path 
        key_password: str | None = args.key_password
        dest: Path = args.dest

        repo = FreeBSDRepo()

        for p in packages:
            print(f'Adding {p}')
            repo.add_package(p)

        signer = PkiSigner(key_path, key_password)

        repo.export(dest, signer)

        return 0

class _RpmHandler(_Handler):
    def add_parser(self, key: str, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]):
        parser: argparse.ArgumentParser = subparsers.add_parser(key, description='Create RPM repo')
        
        parser.add_argument('-o', '--output', dest='dest', type=Path, metavar='DEST', required=True,
                            help='output path to export the repository to')
        parser.add_argument('-k', '--key', type=Path, dest='key_name', metavar='KEY_NAME', required=True,
                            help='Name or ID of the GPG key for signing')
        parser.add_argument('-w', '--password', type=str, dest='key_password', metavar='KEY_PASSWORD', required=True,
                            help='GPG key password')
        parser.add_argument('-p', '--packages', nargs='+', metavar='PACKAGE', action='extend',
                            help='.rpm file(s) to add to repository.')
        

    def handle(self, args: argparse.Namespace):
        packages: Sequence[str] = args.packages 
        key_name: str = args.key_name
        key_password: str = args.key_password
        dest: Path = args.dest

        repo = RpmRepo()
        
        for package in packages:
            print(f'Adding {package}')
            repo.add_package(package)

        signer = PgpSigner(key_name=key_name, key_pwd=key_password)

        repo.export(dest, signer)
        
        return 0
    
class _PacmanHandler(_Handler):
    def add_parser(self, key: str, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]):
        parser: argparse.ArgumentParser = subparsers.add_parser(key, description='Create Pacman repo')
        
        parser.add_argument('-o', '--output', dest='dest', type=Path, metavar='DEST', required=True,
                            help='output path to export the repository to')
        
        parser.add_argument('-n', '--name', type=str, dest='name', required=True,
                            help='repository name')
        parser.add_argument('-k', '--key', type=Path, dest='key_name', metavar='KEY_NAME', required=True,
                            help='Name or ID of the GPG key for signing')
        parser.add_argument('-w', '--password', type=str, dest='key_password', metavar='KEY_PASSWORD', required=True,
                            help='GPG key password')
        parser.add_argument('-p', '--packages', nargs='+', metavar='PACKAGE', action='extend',
                            help='.zst file(s) to add to repository. If a .sig file with the same name exists next '
                            'to a .zst file, it will be automatically used to supply the package signature')
        

    def handle(self, args: argparse.Namespace):
        name: str = args.name
        packages: Sequence[str] = args.packages 
        key_name: str = args.key_name
        key_password: str = args.key_password
        dest: Path = args.dest

        repo = PacmanRepo(name)
        
        for p in packages:
            print(f'Adding {p}')
            repo.add_package(p)

        signer = PgpSigner(key_name=key_name, key_pwd=key_password)

        repo.export(dest, signer)
        
        return 0
    
    
class _AptHandler(_Handler):
    class _DistroAction(argparse.Action):
        def __call__(self, 
                    parser: argparse.ArgumentParser, 
                    namespace: argparse.Namespace, 
                    values: str | Sequence[Any] | None, 
                    option_string: str | None = None) -> None:
            if not isinstance(values, str):
                raise argparse.ArgumentError(self, 'distribution option must have a single value')
            if not hasattr(namespace, 'distros'):
                namespace.distros = {}
            distro = namespace.distros.get(values)
            if distro is None:
                distro = argparse.Namespace()
                distro.component = None
                distro.origin = None
                distro.label = None
                distro.suite = None
                distro.codename = None
                distro.version = None
                distro.desc = None
                distro.packages = []
                namespace.distros[values] = distro
            namespace.current_distro = distro


    class _StoreAction(argparse._StoreAction):
        def __call__(self, 
                    parser: argparse.ArgumentParser, 
                    namespace: argparse.Namespace, 
                    values: str | Sequence[Any] | None, 
                    option_string: str | None = None) -> None:
            if not hasattr(namespace, 'distros'):
                name = argparse._get_action_name(self)
                raise argparse.ArgumentError(self, f'you must use --distro before {name}')
            super().__call__(parser, namespace.current_distro, values, option_string)

    class _ExtendPackageAction(argparse._ExtendAction):
        def __call__(self, 
                    parser: argparse.ArgumentParser, 
                    namespace: argparse.Namespace, 
                    values: str | Sequence[Any] | None, 
                    option_string: str | None = None) -> None:
            if not hasattr(namespace, 'distros'):
                name = argparse._get_action_name(self)
                raise argparse.ArgumentError(self, f'you must use --distro before {name}')
            
            if (component := namespace.current_distro.component) is None:
                component = 'main'
            if isinstance(values, list):
                value = [(x, component) for x in values]
            else:
                value = (values, component)
            super().__call__(parser, namespace.current_distro, value, option_string)

    def add_parser(self, key: str, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]):
        parser: argparse.ArgumentParser = subparsers.add_parser(key, description='Create APT repo')
        
        parser.add_argument('-o', '--output', dest='dest', type=Path, metavar='DEST', required=True,
                            help='output path to export the repository to')
        parser.add_argument('-k', '--key', type=Path, dest='key_name', metavar='KEY_NAME', required=True,
                            help='Name or ID of the GPG key for signing')
        parser.add_argument('-w', '--password', type=str, dest='key_password', metavar='KEY_PASSWORD', required=True,
                            help='GPG key password')
        
        parser.add_argument('-d', '--distro', type=str, dest='distro', metavar='DISTRO', required=True, action=_AptHandler._DistroAction,
                            help='Distribution name. This can be a relative path like `stable/updates`. All subsequent '
                            'per-distribution options apply to this distribution '
                            'Conversely this option is required to precede all per-distribution options. Multiple '
                            'distributions may be specified on the same command line')
        
        parser.add_argument('-c', '--comp', type=str, dest='component', metavar='COMPONENT', 
                            nargs='?', default=None, action=_AptHandler._StoreAction,
                            help='Component for subsequent packages in the current distribution. If not '
                            'specified, defaults to `main`')
        parser.add_argument('--origin', type=str, dest='origin', metavar='ORIGIN', action=_AptHandler._StoreAction,
                            help='current distribution origin')
        parser.add_argument('--label', type=str, dest='label', metavar='LABEL', action=_AptHandler._StoreAction,
                            help='current distribution label')
        parser.add_argument('--suite', type=str, dest='suite', metavar='SUITE', action=_AptHandler._StoreAction,
                            help='current distribution suite')
        parser.add_argument('--codename', type=str, dest='codename', metavar='CODENAME', action=_AptHandler._StoreAction,
                            help='current distribution codename')
        parser.add_argument('--version', type=str, dest='version', metavar='VERSION', action=_AptHandler._StoreAction,
                            help='current distribution version')
        parser.add_argument('--desc', type=str, dest='desc', metavar='DESC', action=_AptHandler._StoreAction,
                            help='current distribution description')
        
        parser.add_argument('-p', '--packages', nargs='+', metavar='PACKAGE', action=_AptHandler._ExtendPackageAction,
                            help='.deb file(s) to add to the current distribution')
        
    def handle(self, args: argparse.Namespace):
        distros: dict[str, argparse.Namespace] = args.distros
        key_name: str = args.key_name
        key_password: str = args.key_password
        dest: Path = args.dest

        repo = AptRepo()

        all_packages: dict[str, AptPackage] = {}
        for distro_path, distro_args in distros.items():
            normalized: set[Tuple[str, str]] = set(distro_args.packages) if distro_args.packages is not None else set()
            
            print(f'Adding distribution: {distro_path}')
            distro = repo.add_distribution(distro_path,
                                           origin=distro_args.origin,
                                           label=distro_args.label,
                                           suite=distro_args.suite,
                                           codename=distro_args.codename,
                                           version=distro_args.version,
                                           description=distro_args.desc)
                
            for name, component in normalized:
                repo_object = all_packages.get(name)
                if repo_object is None:
                    print(f'Adding new package: {name}')
                    repo_object = repo.add_package(name)
                    all_packages[name] = repo_object
                print(f'Assigning package: {name} to component {component}')
                repo.assign_package(repo_object, distro, component) 

        
        signer = PgpSigner(key_name=key_name, key_pwd=key_password)

        repo.export(dest, signer)

        return 0


def main():
    """script entry point"""

    repo_types: dict[str, _Handler] = {
        'alpine': _AlpineHandler(),
        'apt': _AptHandler(),
        'freebsd': _FreeBSDHandler(),
        'pacman': _PacmanHandler(),
        'rpm': _RpmHandler(),
    }


    parser = argparse.ArgumentParser(
        prog='repopulator',
        description='Populates software repositories',
        epilog="Use repopulator TYPE -h to get more help for each type's options"
    )
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {VERSION}')
    subparsers = parser.add_subparsers(
        help='type of repository to create, one of: ' + ', '.join(repo_types),
        metavar='TYPE',
        dest='repo_key',
        required=True
    )
    for repo_key, handler in repo_types.items():
        handler.add_parser(repo_key, subparsers)
    
    args = parser.parse_args()
    return repo_types[args.repo_key].handle(args)

if __name__ == '__main__':
    sys.exit(main())
