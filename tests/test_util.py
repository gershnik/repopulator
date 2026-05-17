# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024, Eugene Gershnik
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE.txt file or at
# https://opensource.org/licenses/BSD-3-Clause

# pylint: skip-file

import pytest

from repopulator.util import *

def test_lowerBound():
    assert lower_bound([1, 2, 3], 0) == 0
    assert lower_bound([1, 2, 3], 1) == 0
    assert lower_bound([1, 2, 3], 2) == 1
    assert lower_bound([1, 2, 3], 3) == 2
    assert lower_bound([1, 2, 3], 4) == 3


# --- VersionKey: construction ---

class TestVersionKeyConstruction:
    def test_empty(self):
        v = VersionKey()
        assert v == VersionKey()

    def test_ints(self):
        v = VersionKey(1, 2, 3)
        assert v == VersionKey(1, 2, 3)

    def test_strings(self):
        v = VersionKey('a', 'b')
        assert v == VersionKey('a', 'b')

    def test_bytes_get_decoded(self):
        # bytes args are decoded to str — VersionKey(b'a') should equal VersionKey('a')
        assert VersionKey(b'rc') == VersionKey('rc')
        assert VersionKey(1, b'rc', 2) == VersionKey(1, 'rc', 2)

    def test_mixed(self):
        v = VersionKey(1, 'rc', 2)
        assert v == VersionKey(1, 'rc', 2)

    def test_rejects_unsupported_types(self):
        with pytest.raises(ValueError):
            VersionKey(1.5)
        with pytest.raises(ValueError):
            VersionKey([1, 2])
        with pytest.raises(ValueError):
            VersionKey(None)

    def test_int_and_str_with_same_text_are_not_equal(self):
        # type matters: VersionKey(1) is not VersionKey('1')
        assert VersionKey(1) != VersionKey('1')


# --- VersionKey: parse ---

class TestVersionKeyParse:

    @pytest.mark.parametrize('version,expected', [
        ('',          VersionKey()),
        ('1',         VersionKey(1)),
        ('123',       VersionKey(123)),
        ('1.2.3',     VersionKey(1, 2, 3)),
        ('1-2-3',     VersionKey(1, 2, 3)),
        ('1_2_3',     VersionKey(1, 2, 3)),
        # The canonical motivating example — "1.10" must have parts [1, 10], not ['1.10'] strings
        ('1.10',      VersionKey(1, 10)),
        # alpha-only
        ('abc',       VersionKey('abc')),
        # adjacent alpha/digit are split into separate parts
        ('1a',        VersionKey(1, 'a')),
        ('a1',        VersionKey('a', 1)),
        ('1a2',       VersionKey(1, 'a', 2)),
        ('1a2b3',     VersionKey(1, 'a', 2, 'b', 3)),
        # leading and trailing separators are ignored
        ('-1.2',      VersionKey(1, 2)),
        ('1.2-',      VersionKey(1, 2)),
        # multiple separators collapse
        ('1..2',      VersionKey(1, 2)),
        ('1.-_2',     VersionKey(1, 2)),
        # only separators → empty key
        ('---',       VersionKey()),
        # real-world flavors
        ('1.2.3-rc1', VersionKey(1, 2, 3, 'rc', 1)),
        ('2.0.0_20',  VersionKey(2, 0, 0, 20)),
        ('1:2.3-4',   VersionKey(1, 2, 3, 4)),  # epoch separator treated as separator
    ])
    def test_parse_examples(self, version, expected):
        assert VersionKey.parse(version) == expected

    def test_parse_is_total(self):
        # docs say "Parsing is always well defined for any string and never fails"
        # exercise some pathological inputs
        for s in ['', '.', '..', '-', '_', ' ', '!@#$%', '\n\t', 'x' * 1000]:
            VersionKey.parse(s)  # must not raise


# --- VersionKey: equality ---

class TestVersionKeyEquality:
    def test_reflexive(self):
        v = VersionKey(1, 2, 3)
        assert v == v

    def test_equal_parts_equal_keys(self):
        assert VersionKey(1, 'a', 2) == VersionKey(1, 'a', 2)

    def test_different_lengths_not_equal(self):
        assert VersionKey(1, 2) != VersionKey(1, 2, 3)
        assert VersionKey(1) != VersionKey()

    def test_different_values_not_equal(self):
        assert VersionKey(1, 2, 3) != VersionKey(1, 2, 4)
        assert VersionKey('a') != VersionKey('b')

    def test_type_matters(self):
        # an int and a string that "look the same" are not equal
        assert VersionKey(1) != VersionKey('1')
        assert VersionKey(1, '2') != VersionKey(1, 2)

    def test_not_equal_to_other_types(self):
        v = VersionKey(1, 2, 3)
        assert v != (1, 2, 3)
        assert v != [1, 2, 3]
        assert v != '1.2.3'
        assert v != 123
        assert v != None

    def test_ne_is_inverse_of_eq(self):
        v1 = VersionKey(1, 2)
        v2 = VersionKey(1, 2)
        v3 = VersionKey(1, 3)
        assert not (v1 != v2)
        assert v1 != v3


# --- VersionKey: ordering ---

class TestVersionKeyOrdering:

    def test_basic_numeric(self):
        assert VersionKey(1) < VersionKey(2)
        assert VersionKey(2) > VersionKey(1)
        assert VersionKey(1) <= VersionKey(1)
        assert VersionKey(1) <= VersionKey(2)
        assert VersionKey(2) >= VersionKey(1)
        assert VersionKey(1) >= VersionKey(1)

    def test_motivating_example_1_10_vs_1_2(self):
        # the reason VersionKey exists: "1.10" > "1.2"
        assert VersionKey.parse('1.10') > VersionKey.parse('1.2')
        assert VersionKey.parse('1.2')  < VersionKey.parse('1.10')

    def test_lexicographic_within_alpha(self):
        assert VersionKey('a') < VersionKey('b')
        assert VersionKey('aa') < VersionKey('ab')

    def test_longer_is_greater_when_prefix_equal(self):
        assert VersionKey(1, 2) > VersionKey(1)
        assert VersionKey(1) < VersionKey(1, 2)
        # alpha case too
        assert VersionKey('a', 'b') > VersionKey('a')

    def test_numbers_sort_before_strings_at_same_position(self):
        # per __lt__: "numbers are less than strings"
        assert VersionKey(1) < VersionKey('a')
        assert VersionKey('a') > VersionKey(1)
        # same prefix, then numeric vs alpha tail
        assert VersionKey(1, 2) < VersionKey(1, 'a')

    def test_equal_keys_are_neither_lt_nor_gt(self):
        v1 = VersionKey(1, 2, 3)
        v2 = VersionKey(1, 2, 3)
        assert not (v1 < v2)
        assert not (v1 > v2)
        assert v1 <= v2
        assert v1 >= v2

    def test_empty_is_smaller_than_any_nonempty(self):
        assert VersionKey() < VersionKey(0)
        assert VersionKey() < VersionKey('')  # via length 0 vs 1
        assert VersionKey() < VersionKey(1)
        assert VersionKey(1) > VersionKey()

    def test_sorting_a_list(self):
        keys = [VersionKey.parse(s) for s in [
            '1.10', '1.2', '1.1', '2.0', '1.10.1', '0.9', '1.0', '1.2.1',
        ]]
        expected = [VersionKey.parse(s) for s in [
            '0.9', '1.0', '1.1', '1.2', '1.2.1', '1.10', '1.10.1', '2.0',
        ]]
        assert sorted(keys) == expected


# --- VersionKey: hashing ---

class TestVersionKeyHashing:
    def test_parsed_key_is_hashable(self):
        # regression: __hash__ used to call hash() on a list and raise TypeError
        hash(VersionKey.parse('1.2.3'))
        hash(VersionKey())
        hash(VersionKey(1, 'rc', 2))

    def test_equal_keys_have_equal_hashes(self):
        assert hash(VersionKey(1, 2, 3)) == hash(VersionKey(1, 2, 3))
        assert hash(VersionKey.parse('1.2.3')) == hash(VersionKey(1, 2, 3))
        assert hash(VersionKey.parse('1.2.3')) == hash(VersionKey.parse('1.2.3'))

    def test_usable_in_set(self):
        s = {VersionKey(1), VersionKey(1), VersionKey(2)}
        assert len(s) == 2
        assert VersionKey(1) in s
        assert VersionKey(2) in s
        assert VersionKey(3) not in s

    def test_usable_as_dict_key(self):
        d = {VersionKey.parse('1.0'): 'first', VersionKey.parse('2.0'): 'second'}
        assert d[VersionKey(1, 0)] == 'first'
        assert d[VersionKey(2, 0)] == 'second'

    def test_int_vs_str_have_different_hashes_when_unequal(self):
        # not strictly guaranteed by the hash contract, but VersionKey(1) != VersionKey('1')
        # and the hashing happens to fall through to tuple-hashing which distinguishes them
        assert hash(VersionKey(1)) != hash(VersionKey('1'))


# --- VersionKey: parse and __init__ equivalence ---

class TestVersionKeyParseConstructEquivalence:
    @pytest.mark.parametrize('version,expected', [
        ('1',         VersionKey(1)),
        ('1.2',       VersionKey(1, 2)),
        ('1a',        VersionKey(1, 'a')),
        ('a1b2',      VersionKey('a', 1, 'b', 2)),
        ('1.2.3-rc1', VersionKey(1, 2, 3, 'rc', 1)),
    ])
    def test_parse_matches_explicit(self, version, expected):
        parsed = VersionKey.parse(version)
        assert parsed == expected
        assert hash(parsed) == hash(expected)
        # and the comparison machinery agrees both ways
        assert not (parsed < expected) and not (parsed > expected)