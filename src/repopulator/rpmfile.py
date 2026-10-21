# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

"""Minimal reader for RPM package headers

Supports RPM v3/v4 and v6 package formats. Only the lead, the signature header and
the main header are parsed. The payload is not touched.

Tag and type constants below match the names used in RPM sources (include/rpm/rpmtag.h).
Tags are grouped into RpmTag (RPMTAG_* without the prefix) and RpmSigTag (RPMSIGTAG_*
without the prefix), so RPMTAG_NAME is RpmTag.NAME. Signature header tags live in their own
namespace which overlaps with main header tag values. Use RpmSigTag with RpmFile.signature
and RpmTag with RpmFile.header.
"""

from __future__ import annotations

import struct
import collections.abc

from pathlib import Path
from dataclasses import dataclass
from typing import Any, BinaryIO, Final, Iterator, Optional, Union


# Generated from rpm/include/rpm/rpmtag.h. Comments are from the original source

HEADER_IMAGE: Final = 61
HEADER_SIGNATURES: Final = 62
HEADER_IMMUTABLE: Final = 63
HEADER_REGIONS: Final = 64
HEADER_I18NTABLE: Final = 100
HEADER_SIGBASE: Final = 256
HEADER_SIGTOP: Final = 999
HEADER_TAGBASE: Final = 1000


class RpmTag:
    """Main header tags (rpmTag_e in rpmtag.h with RPMTAG_ prefix removed)"""

    HEADERIMAGE: Final = HEADER_IMAGE                      # Current image.
    HEADERSIGNATURES: Final = HEADER_SIGNATURES            # Signatures.
    HEADERIMMUTABLE: Final = HEADER_IMMUTABLE              # x Original image.
    HEADERREGIONS: Final = HEADER_REGIONS                  # Regions.
    HEADERI18NTABLE: Final = HEADER_I18NTABLE              # s[] I18N string locales.
    SIG_BASE: Final = HEADER_SIGBASE
    SIGSIZE: Final = 257                                   # i
    SIGLEMD5_1: Final = 258                                # internal - obsolete
    SIGPGP: Final = 259                                    # x
    SIGLEMD5_2: Final = 260                                # x internal - obsolete
    SIGMD5: Final = 261                                    # x
    SIGGPG: Final = 262                                    # x
    SIGPGP5: Final = 263                                   # internal - obsolete
    BADSHA1_1: Final = 264                                 # internal - obsolete
    BADSHA1_2: Final = 265                                 # internal - obsolete
    PUBKEYS: Final = 266                                   # s[]
    DSAHEADER: Final = 267                                 # x
    RSAHEADER: Final = 268                                 # x
    SHA1HEADER: Final = 269                                # s
    LONGSIGSIZE: Final = 270                               # l
    LONGARCHIVESIZE: Final = 271                           # l
    SHA256HEADER: Final = 273                              # s
    VERITYSIGNATURES: Final = 276                          # s[]
    VERITYSIGNATUREALGO: Final = 277                       # i
    OPENPGP: Final = 278                                   # s[]
    SHA3_256HEADER: Final = 279                            # s
    SIG_TOP: Final = HEADER_SIGTOP
    NAME: Final = 1000                                     # s
    N: Final = NAME                                        # s
    VERSION: Final = 1001                                  # s
    V: Final = VERSION                                     # s
    RELEASE: Final = 1002                                  # s
    R: Final = RELEASE                                     # s
    EPOCH: Final = 1003                                    # i
    E: Final = EPOCH                                       # i
    SUMMARY: Final = 1004                                  # s{}
    DESCRIPTION: Final = 1005                              # s{}
    BUILDTIME: Final = 1006                                # i
    BUILDHOST: Final = 1007                                # s
    INSTALLTIME: Final = 1008                              # i
    SIZE: Final = 1009                                     # i
    DISTRIBUTION: Final = 1010                             # s
    VENDOR: Final = 1011                                   # s
    GIF: Final = 1012                                      # x
    XPM: Final = 1013                                      # x
    LICENSE: Final = 1014                                  # s
    PACKAGER: Final = 1015                                 # s
    GROUP: Final = 1016                                    # s{}
    CHANGELOG: Final = 1017                                # s[] internal
    SOURCE: Final = 1018                                   # s[]
    PATCH: Final = 1019                                    # s[]
    URL: Final = 1020                                      # s
    OS: Final = 1021                                       # s legacy used int
    ARCH: Final = 1022                                     # s legacy used int
    PREIN: Final = 1023                                    # s
    POSTIN: Final = 1024                                   # s
    PREUN: Final = 1025                                    # s
    POSTUN: Final = 1026                                   # s
    OLDFILENAMES: Final = 1027                             # s[] obsolete
    FILESIZES: Final = 1028                                # i[]
    FILESTATES: Final = 1029                               # c[]
    FILEMODES: Final = 1030                                # h[]
    FILEUIDS: Final = 1031                                 # i[] internal - obsolete
    FILEGIDS: Final = 1032                                 # i[] internal - obsolete
    FILERDEVS: Final = 1033                                # h[]
    FILEMTIMES: Final = 1034                               # i[]
    FILEDIGESTS: Final = 1035                              # s[]
    FILEMD5S: Final = FILEDIGESTS                          # s[]
    FILELINKTOS: Final = 1036                              # s[]
    FILEFLAGS: Final = 1037                                # i[]
    ROOT: Final = 1038                                     # internal - obsolete
    FILEUSERNAME: Final = 1039                             # s[]
    FILEGROUPNAME: Final = 1040                            # s[]
    EXCLUDE: Final = 1041                                  # internal - obsolete
    EXCLUSIVE: Final = 1042                                # internal - obsolete
    ICON: Final = 1043                                     # x
    SOURCERPM: Final = 1044                                # s
    FILEVERIFYFLAGS: Final = 1045                          # i[]
    ARCHIVESIZE: Final = 1046                              # i
    PROVIDENAME: Final = 1047                              # s[]
    PROVIDES: Final = PROVIDENAME                          # s[]
    P: Final = PROVIDENAME                                 # s[]
    REQUIREFLAGS: Final = 1048                             # i[]
    REQUIRENAME: Final = 1049                              # s[]
    REQUIRES: Final = REQUIRENAME                          # s[]
    REQUIREVERSION: Final = 1050                           # s[]
    NOSOURCE: Final = 1051                                 # i[]
    NOPATCH: Final = 1052                                  # i[]
    CONFLICTFLAGS: Final = 1053                            # i[]
    CONFLICTNAME: Final = 1054                             # s[]
    CONFLICTS: Final = CONFLICTNAME                        # s[]
    C: Final = CONFLICTNAME                                # s[]
    CONFLICTVERSION: Final = 1055                          # s[]
    DEFAULTPREFIX: Final = 1056                            # s internal - deprecated
    BUILDROOT: Final = 1057                                # s internal - obsolete
    INSTALLPREFIX: Final = 1058                            # s internal - deprecated
    EXCLUDEARCH: Final = 1059                              # s[]
    EXCLUDEOS: Final = 1060                                # s[]
    EXCLUSIVEARCH: Final = 1061                            # s[]
    EXCLUSIVEOS: Final = 1062                              # s[]
    AUTOREQPROV: Final = 1063                              # s internal
    RPMVERSION: Final = 1064                               # s
    TRIGGERSCRIPTS: Final = 1065                           # s[]
    TRIGGERNAME: Final = 1066                              # s[]
    TRIGGERVERSION: Final = 1067                           # s[]
    TRIGGERFLAGS: Final = 1068                             # i[]
    TRIGGERINDEX: Final = 1069                             # i[]
    VERIFYSCRIPT: Final = 1079                             # s
    CHANGELOGTIME: Final = 1080                            # i[]
    CHANGELOGNAME: Final = 1081                            # s[]
    CHANGELOGTEXT: Final = 1082                            # s[]
    BROKENMD5: Final = 1083                                # internal - obsolete
    PREREQ: Final = 1084                                   # internal
    PREINPROG: Final = 1085                                # s[]
    POSTINPROG: Final = 1086                               # s[]
    PREUNPROG: Final = 1087                                # s[]
    POSTUNPROG: Final = 1088                               # s[]
    BUILDARCHS: Final = 1089                               # s[]
    OBSOLETENAME: Final = 1090                             # s[]
    OBSOLETES: Final = OBSOLETENAME                        # s[]
    O: Final = OBSOLETENAME                                # s[]
    VERIFYSCRIPTPROG: Final = 1091                         # s[]
    TRIGGERSCRIPTPROG: Final = 1092                        # s[]
    DOCDIR: Final = 1093                                   # internal
    COOKIE: Final = 1094                                   # s
    FILEDEVICES: Final = 1095                              # i[]
    FILEINODES: Final = 1096                               # i[]
    FILELANGS: Final = 1097                                # s[]
    PREFIXES: Final = 1098                                 # s[]
    INSTPREFIXES: Final = 1099                             # s[]
    TRIGGERIN: Final = 1100                                # internal
    TRIGGERUN: Final = 1101                                # internal
    TRIGGERPOSTUN: Final = 1102                            # internal
    AUTOREQ: Final = 1103                                  # internal
    AUTOPROV: Final = 1104                                 # internal
    CAPABILITY: Final = 1105                               # i internal - obsolete
    SOURCEPACKAGE: Final = 1106                            # i
    OLDORIGFILENAMES: Final = 1107                         # internal - obsolete
    BUILDPREREQ: Final = 1108                              # internal
    BUILDREQUIRES: Final = 1109                            # internal
    BUILDCONFLICTS: Final = 1110                           # internal
    BUILDMACROS: Final = 1111                              # internal - unused
    PROVIDEFLAGS: Final = 1112                             # i[]
    PROVIDEVERSION: Final = 1113                           # s[]
    OBSOLETEFLAGS: Final = 1114                            # i[]
    OBSOLETEVERSION: Final = 1115                          # s[]
    DIRINDEXES: Final = 1116                               # i[]
    BASENAMES: Final = 1117                                # s[]
    DIRNAMES: Final = 1118                                 # s[]
    ORIGDIRINDEXES: Final = 1119                           # i[] relocation
    ORIGBASENAMES: Final = 1120                            # s[] relocation
    ORIGDIRNAMES: Final = 1121                             # s[] relocation
    OPTFLAGS: Final = 1122                                 # s
    DISTURL: Final = 1123                                  # s
    PAYLOADFORMAT: Final = 1124                            # s
    PAYLOADCOMPRESSOR: Final = 1125                        # s
    PAYLOADFLAGS: Final = 1126                             # s
    INSTALLCOLOR: Final = 1127                             # i transaction color when installed
    INSTALLTID: Final = 1128                               # i
    REMOVETID: Final = 1129                                # i
    SHA1RHN: Final = 1130                                  # internal - obsolete
    RHNPLATFORM: Final = 1131                              # s internal - obsolete
    PLATFORM: Final = 1132                                 # s
    PATCHESNAME: Final = 1133                              # s[] deprecated placeholder (SuSE)
    PATCHESFLAGS: Final = 1134                             # i[] deprecated placeholder (SuSE)
    PATCHESVERSION: Final = 1135                           # s[] deprecated placeholder (SuSE)
    CACHECTIME: Final = 1136                               # i internal - obsolete
    CACHEPKGPATH: Final = 1137                             # s internal - obsolete
    CACHEPKGSIZE: Final = 1138                             # i internal - obsolete
    CACHEPKGMTIME: Final = 1139                            # i internal - obsolete
    FILECOLORS: Final = 1140                               # i[]
    FILECLASS: Final = 1141                                # i[]
    CLASSDICT: Final = 1142                                # s[]
    FILEDEPENDSX: Final = 1143                             # i[]
    FILEDEPENDSN: Final = 1144                             # i[]
    DEPENDSDICT: Final = 1145                              # i[]
    SOURCESIGMD5: Final = 1146                             # x
    FILECONTEXTS: Final = 1147                             # s[] - obsolete
    FSCONTEXTS: Final = 1148                               # s[] extension
    RECONTEXTS: Final = 1149                               # s[] extension
    POLICIES: Final = 1150                                 # s[] selinux *.te policy file.
    PRETRANS: Final = 1151                                 # s
    POSTTRANS: Final = 1152                                # s
    PRETRANSPROG: Final = 1153                             # s[]
    POSTTRANSPROG: Final = 1154                            # s[]
    DISTTAG: Final = 1155                                  # s
    OLDSUGGESTSNAME: Final = 1156                          # s[] - obsolete
    OLDSUGGESTS: Final = OLDSUGGESTSNAME                   # s[] - obsolete
    OLDSUGGESTSVERSION: Final = 1157                       # s[] - obsolete
    OLDSUGGESTSFLAGS: Final = 1158                         # i[] - obsolete
    OLDENHANCESNAME: Final = 1159                          # s[] - obsolete
    OLDENHANCES: Final = OLDENHANCESNAME                   # s[] - obsolete
    OLDENHANCESVERSION: Final = 1160                       # s[] - obsolete
    OLDENHANCESFLAGS: Final = 1161                         # i[] - obsolete
    PRIORITY: Final = 1162                                 # i[] extension placeholder (unimplemented)
    CVSID: Final = 1163                                    # s (unimplemented)
    SVNID: Final = CVSID                                   # s (unimplemented)
    BLINKPKGID: Final = 1164                               # s[] (unimplemented)
    BLINKHDRID: Final = 1165                               # s[] (unimplemented)
    BLINKNEVRA: Final = 1166                               # s[] (unimplemented)
    FLINKPKGID: Final = 1167                               # s[] (unimplemented)
    FLINKHDRID: Final = 1168                               # s[] (unimplemented)
    FLINKNEVRA: Final = 1169                               # s[] (unimplemented)
    PACKAGEORIGIN: Final = 1170                            # s (unimplemented)
    TRIGGERPREIN: Final = 1171                             # internal
    BUILDSUGGESTS: Final = 1172                            # internal (unimplemented)
    BUILDENHANCES: Final = 1173                            # internal (unimplemented)
    SCRIPTSTATES: Final = 1174                             # i[] scriptlet exit codes (unimplemented)
    SCRIPTMETRICS: Final = 1175                            # i[] scriptlet execution times (unimplemented)
    BUILDCPUCLOCK: Final = 1176                            # i (unimplemented)
    FILEDIGESTALGOS: Final = 1177                          # i[] (unimplemented)
    VARIANTS: Final = 1178                                 # s[] (unimplemented)
    XMAJOR: Final = 1179                                   # i (unimplemented)
    XMINOR: Final = 1180                                   # i (unimplemented)
    REPOTAG: Final = 1181                                  # s (unimplemented)
    KEYWORDS: Final = 1182                                 # s[] (unimplemented)
    BUILDPLATFORMS: Final = 1183                           # s[] (unimplemented)
    PACKAGECOLOR: Final = 1184                             # i (unimplemented)
    PACKAGEPREFCOLOR: Final = 1185                         # i (unimplemented)
    XATTRSDICT: Final = 1186                               # s[] (unimplemented)
    FILEXATTRSX: Final = 1187                              # i[] (unimplemented)
    DEPATTRSDICT: Final = 1188                             # s[] (unimplemented)
    CONFLICTATTRSX: Final = 1189                           # i[] (unimplemented)
    OBSOLETEATTRSX: Final = 1190                           # i[] (unimplemented)
    PROVIDEATTRSX: Final = 1191                            # i[] (unimplemented)
    REQUIREATTRSX: Final = 1192                            # i[] (unimplemented)
    BUILDPROVIDES: Final = 1193                            # internal (unimplemented)
    BUILDOBSOLETES: Final = 1194                           # internal (unimplemented)
    DBINSTANCE: Final = 1195                               # i extension
    NVRA: Final = 1196                                     # s extension
    FILENAMES: Final = 5000                                # s[] extension
    FILEPROVIDE: Final = 5001                              # s[] extension
    FILEREQUIRE: Final = 5002                              # s[] extension
    FSNAMES: Final = 5003                                  # s[] (unimplemented)
    FSSIZES: Final = 5004                                  # l[] (unimplemented)
    TRIGGERCONDS: Final = 5005                             # s[] extension
    TRIGGERTYPE: Final = 5006                              # s[] extension
    ORIGFILENAMES: Final = 5007                            # s[] extension
    LONGFILESIZES: Final = 5008                            # l[]
    LONGSIZE: Final = 5009                                 # l
    FILECAPS: Final = 5010                                 # s[]
    FILEDIGESTALGO: Final = 5011                           # i file digest algorithm
    BUGURL: Final = 5012                                   # s
    EVR: Final = 5013                                      # s extension
    NVR: Final = 5014                                      # s extension
    NEVR: Final = 5015                                     # s extension
    NEVRA: Final = 5016                                    # s extension
    HEADERCOLOR: Final = 5017                              # i extension
    VERBOSE: Final = 5018                                  # i extension
    EPOCHNUM: Final = 5019                                 # i extension
    PREINFLAGS: Final = 5020                               # i
    POSTINFLAGS: Final = 5021                              # i
    PREUNFLAGS: Final = 5022                               # i
    POSTUNFLAGS: Final = 5023                              # i
    PRETRANSFLAGS: Final = 5024                            # i
    POSTTRANSFLAGS: Final = 5025                           # i
    VERIFYSCRIPTFLAGS: Final = 5026                        # i
    TRIGGERSCRIPTFLAGS: Final = 5027                       # i[]
    COLLECTIONS: Final = 5029                              # s[] list of collections (unimplemented)
    POLICYNAMES: Final = 5030                              # s[]
    POLICYTYPES: Final = 5031                              # s[]
    POLICYTYPESINDEXES: Final = 5032                       # i[]
    POLICYFLAGS: Final = 5033                              # i[]
    VCS: Final = 5034                                      # s
    ORDERNAME: Final = 5035                                # s[]
    ORDERVERSION: Final = 5036                             # s[]
    ORDERFLAGS: Final = 5037                               # i[]
    MSSFMANIFEST: Final = 5038                             # s[] reservation (unimplemented)
    MSSFDOMAIN: Final = 5039                               # s[] reservation (unimplemented)
    INSTFILENAMES: Final = 5040                            # s[] extension
    REQUIRENEVRS: Final = 5041                             # s[] extension
    PROVIDENEVRS: Final = 5042                             # s[] extension
    OBSOLETENEVRS: Final = 5043                            # s[] extension
    CONFLICTNEVRS: Final = 5044                            # s[] extension
    FILENLINKS: Final = 5045                               # i[] extension
    RECOMMENDNAME: Final = 5046                            # s[]
    RECOMMENDS: Final = RECOMMENDNAME                      # s[]
    RECOMMENDVERSION: Final = 5047                         # s[]
    RECOMMENDFLAGS: Final = 5048                           # i[]
    SUGGESTNAME: Final = 5049                              # s[]
    SUGGESTS: Final = SUGGESTNAME                          # s[]
    SUGGESTVERSION: Final = 5050                           # s[]
    SUGGESTFLAGS: Final = 5051                             # i[]
    SUPPLEMENTNAME: Final = 5052                           # s[]
    SUPPLEMENTS: Final = SUPPLEMENTNAME                    # s[]
    SUPPLEMENTVERSION: Final = 5053                        # s[]
    SUPPLEMENTFLAGS: Final = 5054                          # i[]
    ENHANCENAME: Final = 5055                              # s[]
    ENHANCES: Final = ENHANCENAME                          # s[]
    ENHANCEVERSION: Final = 5056                           # s[]
    ENHANCEFLAGS: Final = 5057                             # i[]
    RECOMMENDNEVRS: Final = 5058                           # s[] extension
    SUGGESTNEVRS: Final = 5059                             # s[] extension
    SUPPLEMENTNEVRS: Final = 5060                          # s[] extension
    ENHANCENEVRS: Final = 5061                             # s[] extension
    ENCODING: Final = 5062                                 # s
    FILETRIGGERIN: Final = 5063                            # internal
    FILETRIGGERUN: Final = 5064                            # internal
    FILETRIGGERPOSTUN: Final = 5065                        # internal
    FILETRIGGERSCRIPTS: Final = 5066                       # s[]
    FILETRIGGERSCRIPTPROG: Final = 5067                    # s[]
    FILETRIGGERSCRIPTFLAGS: Final = 5068                   # i[]
    FILETRIGGERNAME: Final = 5069                          # s[]
    FILETRIGGERINDEX: Final = 5070                         # i[]
    FILETRIGGERVERSION: Final = 5071                       # s[]
    FILETRIGGERFLAGS: Final = 5072                         # i[]
    TRANSFILETRIGGERIN: Final = 5073                       # internal
    TRANSFILETRIGGERUN: Final = 5074                       # internal
    TRANSFILETRIGGERPOSTUN: Final = 5075                   # internal
    TRANSFILETRIGGERSCRIPTS: Final = 5076                  # s[]
    TRANSFILETRIGGERSCRIPTPROG: Final = 5077               # s[]
    TRANSFILETRIGGERSCRIPTFLAGS: Final = 5078              # i[]
    TRANSFILETRIGGERNAME: Final = 5079                     # s[]
    TRANSFILETRIGGERINDEX: Final = 5080                    # i[]
    TRANSFILETRIGGERVERSION: Final = 5081                  # s[]
    TRANSFILETRIGGERFLAGS: Final = 5082                    # i[]
    REMOVEPATHPOSTFIXES: Final = 5083                      # s internal
    FILETRIGGERPRIORITIES: Final = 5084                    # i[]
    TRANSFILETRIGGERPRIORITIES: Final = 5085               # i[]
    FILETRIGGERCONDS: Final = 5086                         # s[] extension
    FILETRIGGERTYPE: Final = 5087                          # s[] extension
    TRANSFILETRIGGERCONDS: Final = 5088                    # s[] extension
    TRANSFILETRIGGERTYPE: Final = 5089                     # s[] extension
    FILESIGNATURES: Final = 5090                           # s[]
    FILESIGNATURELENGTH: Final = 5091                      # i
    PAYLOADSHA256: Final = 5092                            # s[]
    PAYLOADSHA256ALGO: Final = 5093                        # i (obsolete)
    AUTOINSTALLED: Final = 5094                            # i reservation (unimplemented)
    IDENTITY: Final = 5095                                 # s reservation (unimplemented)
    MODULARITYLABEL: Final = 5096                          # s
    PAYLOADSHA256ALT: Final = 5097                         # s[]
    ARCHSUFFIX: Final = 5098                               # s extension
    SPEC: Final = 5099                                     # s
    TRANSLATIONURL: Final = 5100                           # s
    UPSTREAMRELEASES: Final = 5101                         # s
    SOURCELICENSE: Final = 5102                            # internal
    PREUNTRANS: Final = 5103                               # s
    POSTUNTRANS: Final = 5104                              # s
    PREUNTRANSPROG: Final = 5105                           # s[]
    POSTUNTRANSPROG: Final = 5106                          # s[]
    PREUNTRANSFLAGS: Final = 5107                          # i
    POSTUNTRANSFLAGS: Final = 5108                         # i
    SYSUSERS: Final = 5109                                 # s[] extension
    BUILDSYSTEM: Final = 5110                              # internal
    BUILDOPTION: Final = 5111                              # internal
    PAYLOADSIZE: Final = 5112                              # l
    PAYLOADSIZEALT: Final = 5113                           # l
    RPMFORMAT: Final = 5114                                # i
    FILEMIMEINDEX: Final = 5115                            # i[]
    MIMEDICT: Final = 5116                                 # s[]
    FILEMIMES: Final = 5117                                # s[] extension
    PACKAGEDIGESTS: Final = 5118                           # s[]
    PACKAGEDIGESTALGOS: Final = 5119                       # i[]
    SOURCENEVR: Final = 5120                               # s
    PAYLOADSHA512: Final = 5121                            # s
    PAYLOADSHA512ALT: Final = 5122                         # s
    PAYLOADSHA3_256: Final = 5123                          # s
    PAYLOADSHA3_256ALT: Final = 5124                       # s


class RpmSigTag:
    """Signature header tags (rpmSigTag_e in rpmtag.h with RPMSIGTAG_ prefix removed)"""

    SIZE: Final = 1000                                     # internal Header+Payload size (32bit) in bytes.
    LEMD5_1: Final = 1001                                  # internal Broken MD5, take 1 @deprecated legacy.
    PGP: Final = 1002                                      # internal PGP 2.6.3 signature.
    LEMD5_2: Final = 1003                                  # internal Broken MD5, take 2 @deprecated legacy.
    MD5: Final = 1004                                      # internal MD5 signature.
    GPG: Final = 1005                                      # internal GnuPG signature.
    PGP5: Final = 1006                                     # internal PGP5 signature @deprecated legacy.
    PAYLOADSIZE: Final = 1007                              # internal uncompressed payload size (32bit) in bytes.
    RESERVEDSPACE: Final = 1008                            # internal space reserved for signatures
    BADSHA1_1: Final = RpmTag.BADSHA1_1                    # internal Broken SHA1, take 1.
    BADSHA1_2: Final = RpmTag.BADSHA1_2                    # internal Broken SHA1, take 2.
    DSA: Final = RpmTag.DSAHEADER                          # internal DSA header signature.
    RSA: Final = RpmTag.RSAHEADER                          # internal RSA header signature.
    SHA1: Final = RpmTag.SHA1HEADER                        # internal sha1 header digest.
    LONGSIZE: Final = RpmTag.LONGSIGSIZE                   # internal Header+Payload size (64bit) in bytes.
    LONGARCHIVESIZE: Final = RpmTag.LONGARCHIVESIZE        # internal uncompressed payload size (64bit) in bytes.
    SHA256: Final = RpmTag.SHA256HEADER
    FILESIGNATURES: Final = 274
    FILESIGNATURELENGTH: Final = 275
    VERITYSIGNATURES: Final = RpmTag.VERITYSIGNATURES
    VERITYSIGNATUREALGO: Final = RpmTag.VERITYSIGNATUREALGO
    OPENPGP: Final = RpmTag.OPENPGP
    SHA3_256: Final = RpmTag.SHA3_256HEADER
    RESERVED: Final = RpmTag.SIG_TOP


RPM_NULL_TYPE: Final = 0
RPM_CHAR_TYPE: Final = 1
RPM_INT8_TYPE: Final = 2
RPM_INT16_TYPE: Final = 3
RPM_INT32_TYPE: Final = 4
RPM_INT64_TYPE: Final = 5
RPM_STRING_TYPE: Final = 6
RPM_BIN_TYPE: Final = 7
RPM_STRING_ARRAY_TYPE: Final = 8
RPM_I18NSTRING_TYPE: Final = 9


RPMLEAD_MAGIC: Final = b'\xed\xab\xee\xdb'
RPMLEAD_SIZE: Final = 96
HEADER_MAGIC: Final = b'\x8e\xad\xe8'
HEADER_VERSION: Final = 1


class RpmError(Exception):
    """Malformed RPM file"""


@dataclass(frozen=True)
class RpmLead:
    """RPM lead. Mostly obsolete but still present in every package"""
    major: int
    minor: int
    type: int
    archnum: int
    name: bytes
    osnum: int
    signature_type: int


class RpmHeader(collections.abc.Mapping[int, Any]):
    """A single RPM header (signature or main) keyed by numeric tag

    Value representation depends on the on-disk entry type:

    - RPM_CHAR_TYPE, RPM_INT8_TYPE, RPM_INT16_TYPE, RPM_INT32_TYPE, RPM_INT64_TYPE:
      an int if the entry has a count of 1, otherwise a tuple of ints
    - RPM_STRING_TYPE, RPM_BIN_TYPE: bytes
    - RPM_STRING_ARRAY_TYPE: a tuple of bytes
    - RPM_I18NSTRING_TYPE: bytes of the first (default) locale

    The header format does not distinguish a single element array from a scalar, so
    array-valued tags with one element are returned as a scalar.
    """

    def __init__(self, start: int, end: int, types: dict[int, int], values: dict[int, Any]):
        self.__range = (start, end)
        self.__types = types
        self.__values = values

    @property
    def range(self) -> tuple[int, int]:
        """Byte offsets of the start and end of the header in the file"""
        return self.__range

    def tag_type(self, tag: int) -> int:
        """On-disk RPM_*_TYPE of a given tag. Raises KeyError if not present"""
        return self.__types[tag]

    def __getitem__(self, tag: int) -> Any:
        return self.__values[tag]

    def __iter__(self) -> Iterator[int]:
        return iter(self.__values)

    def __len__(self) -> int:
        return len(self.__values)

    def __repr__(self) -> str:
        return f'RpmHeader({self.__values!r})'


class RpmFile:
    """An RPM package opened for reading its headers

    Either `name` or `fileobj` must be given. If `fileobj` is given it is not closed by
    this object. Headers are parsed eagerly on construction.
    """

    def __init__(self, name: Union[str, Path, None] = None, fileobj: Optional[BinaryIO] = None):
        if fileobj is None:
            if name is None:
                raise ValueError('either name or fileobj must be specified')
            fileobj = open(name, 'rb')  # pylint: disable=consider-using-with
            self.__owns_fileobj = True
        else:
            self.__owns_fileobj = False
        self.__fileobj = fileobj
        try:
            self.__lead = _read_lead(fileobj)
            self.__signature = _read_header(fileobj)
            # signature header is padded to 8 bytes
            sig_start, sig_end = self.__signature.range
            fileobj.seek((8 - (sig_end - sig_start) % 8) % 8, 1)
            self.__header = _read_header(fileobj)
        except:
            self.close()
            raise

    @property
    def lead(self) -> RpmLead:
        """Package lead"""
        return self.__lead

    @property
    def signature(self) -> RpmHeader:
        """Signature header. Keyed by RpmSigTag constants"""
        return self.__signature

    @property
    def header(self) -> RpmHeader:
        """Main header. Keyed by RpmTag constants"""
        return self.__header

    @property
    def header_range(self) -> tuple[int, int]:
        """Byte offsets of the start and end of the main header in the file"""
        return self.__header.range

    @property
    def data_offset(self) -> int:
        """Byte offset of the payload in the file"""
        return self.__header.range[1]

    def close(self):
        """Close the underlying file if it is owned by this object"""
        if self.__owns_fileobj:
            self.__fileobj.close()

    def __enter__(self) -> RpmFile:
        return self

    def __exit__(self, *excinfo):
        self.close()


def _read_exact(fileobj: BinaryIO, size: int) -> bytes:
    data = fileobj.read(size)
    if len(data) != size:
        raise RpmError('unexpected end of file')
    return data


_LEAD_STRUCT = struct.Struct('!4sBBhh66shh16s')
_HEADER_INTRO_STRUCT = struct.Struct('!3sB4sII')
_HEADER_ENTRY_STRUCT = struct.Struct('!IIII')

_NUMERIC_FORMATS = {
    RPM_CHAR_TYPE:  'B',
    RPM_INT8_TYPE:  'B',
    RPM_INT16_TYPE: 'H',
    RPM_INT32_TYPE: 'I',
    RPM_INT64_TYPE: 'Q',
}


def _read_lead(fileobj: BinaryIO) -> RpmLead:
    magic, major, minor, type_, archnum, name, osnum, signature_type, _ = \
        _LEAD_STRUCT.unpack(_read_exact(fileobj, _LEAD_STRUCT.size))
    if magic != RPMLEAD_MAGIC:
        raise RpmError('not an RPM file')
    return RpmLead(major, minor, type_, archnum, name.split(b'\x00', 1)[0], osnum, signature_type)


def _read_header(fileobj: BinaryIO) -> RpmHeader:
    start = fileobj.tell()
    magic, version, _, index_len, data_len = \
        _HEADER_INTRO_STRUCT.unpack(_read_exact(fileobj, _HEADER_INTRO_STRUCT.size))
    if magic != HEADER_MAGIC or version != HEADER_VERSION:
        raise RpmError(f'bad header magic at offset {start}')
    index = _read_exact(fileobj, _HEADER_ENTRY_STRUCT.size * index_len)
    store = _read_exact(fileobj, data_len)
    end = fileobj.tell()

    types: dict[int, int] = {}
    values: dict[int, Any] = {}
    for tag, type_, offset, count in _HEADER_ENTRY_STRUCT.iter_unpack(index):
        if offset >= data_len:
            raise RpmError(f'tag {tag} data offset out of range')
        types[tag] = type_
        values[tag] = _extract_value(tag, type_, offset, count, store)
    return RpmHeader(start, end, types, values)


def _extract_value(tag: int, type_: int, offset: int, count: int, store: bytes) -> Any:
    if (fmt := _NUMERIC_FORMATS.get(type_)) is not None:
        size = struct.calcsize(fmt) * count
        if offset + size > len(store):
            raise RpmError(f'tag {tag} data out of range')
        ret = struct.unpack_from(f'!{count}{fmt}', store, offset)
        return ret[0] if count == 1 else ret
    if type_ == RPM_BIN_TYPE:
        if offset + count > len(store):
            raise RpmError(f'tag {tag} data out of range')
        return store[offset:offset + count]
    if type_ in (RPM_STRING_TYPE, RPM_STRING_ARRAY_TYPE, RPM_I18NSTRING_TYPE):
        strings = []
        for _ in range(count):
            end = store.find(b'\x00', offset)
            if end == -1:
                raise RpmError(f'tag {tag} unterminated string')
            strings.append(store[offset:end])
            offset = end + 1
        if type_ == RPM_STRING_ARRAY_TYPE:
            return tuple(strings)
        if not strings:
            raise RpmError(f'tag {tag} has no strings')
        return strings[0]
    raise RpmError(f'tag {tag} has unknown type {type_}')
