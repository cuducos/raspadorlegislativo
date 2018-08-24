from pathlib import Path

from raspadorlegislativo.matchers import Matcher, keyword_matcher_parser


def test_keyword_parser():
    path = Path() / 'secrets' / 'keywords.json.sample'
    matchers = keyword_matcher_parser(path)
    assert 3 == len(matchers)
    assert all(isinstance(matcher, Matcher) for matcher in matchers)
