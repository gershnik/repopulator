import hashlib
import shutil

from pathlib import Path

from repopulator.util import file_digest


def hash_file(path: Path):
    if not path.exists():
        return ''
    with open(path, 'rb') as f:
        return file_digest(f, hashlib.sha256).hexdigest()
    
def compare_files(actual: Path, expected: Path, populate_expected: bool=False):
    if not populate_expected:
        assert actual.exists()
        assert hash_file(actual) == hash_file(expected)
    else:
        expected.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(actual, expected)
