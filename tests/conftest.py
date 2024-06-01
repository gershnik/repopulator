import os
import pytest
import shutil


from pathlib import Path, PurePosixPath
from dotenv import load_dotenv
from urllib.parse import urlparse
from urllib.request import urlretrieve
from datetime import datetime, timezone
from typing import Dict

from repopulator import PgpSigner, PkiSigner


load_dotenv()

FIXED_DATETIME = datetime(2024, 5, 31, 13, 45, 7, 0, tzinfo=timezone.utc)
PACKAGE_PATH = Path(__file__).parent
PHASE_REPORT_KEY = pytest.StashKey[Dict[str, pytest.CollectReport]]()


def pytest_addoption(parser):
    parser.addoption("--populate-expected", action="store_true", dest="populate_expected", default=False)

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "download(urls): mark test binaries to download and make available for the test"
    )

@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    rep = yield

    # store test results for each phase of a call, which can
    # be "setup", "call", "teardown"
    item.stash.setdefault(PHASE_REPORT_KEY, {})[rep.when] = rep

    return rep



@pytest.fixture 
def binaries_path(request: pytest.FixtureRequest):
    binaries = PACKAGE_PATH / 'output/binaries'
    binaries.mkdir(exist_ok=True, parents=True)
    mark = request.node.get_closest_marker("download")
    if mark is None:
        return binaries
    
    urls = mark.args
    for url in urls:
        res = urlparse(url)
        path = PurePosixPath(res.path)
        local_path = binaries / path.name
        if not local_path.exists():
            urlretrieve(url, local_path)
            os.utime(local_path, (FIXED_DATETIME.timestamp(), FIXED_DATETIME.timestamp()))
    
    return binaries

@pytest.fixture
def output_path(request: pytest.FixtureRequest):
    path: Path = PACKAGE_PATH / 'output' / (request.node.nodeid).replace('::', '.')
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    yield path
    report = request.node.stash[PHASE_REPORT_KEY]
    if True not in (x.failed for x in report.values()):
        shutil.rmtree(path)

@pytest.fixture
def expected_path(request) -> Path:
    path: Path = PACKAGE_PATH / 'expected' / (request.node.nodeid).replace('::', '.')
    return path

@pytest.fixture(scope='session')
def should_populate(request) -> bool:
    should_populate: bool = request.config.option.populate_expected
    return should_populate

@pytest.fixture
def pgp_signer():
    return PgpSigner(Path(os.environ.get('GNUPGHOME', Path.home() / '.gnupg')), 
                     os.environ['PGP_KEY_NAME'], 
                     os.environ['PGP_KEY_PASSWD'])

@pytest.fixture
def pki_signer():
    return PkiSigner((Path(os.environ['BSD_KEY'])), os.environ.get('BSD_KEY_PASSWD'))


@pytest.fixture(scope='session')
def fixed_datetime():
    return FIXED_DATETIME
