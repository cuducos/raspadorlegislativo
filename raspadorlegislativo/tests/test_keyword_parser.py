from json import dump
from os import remove
from tempfile import mkstemp

from raspadorlegislativo.utils.decouple import keyword_parser


def test_keyword_parser():
    data = {
        'tag1': ('keyword1', 'keyword2'),
        'tag2': ('keyword3', 'keyword4', 'keyword5')
    }

    _, tmp = mkstemp(suffix='.json')
    with open(tmp, 'w') as fobj:
        dump(data, fobj)

    expected = set(f'keyword{num}' for num in range(1, 6))
    assert keyword_parser(tmp) == expected
    remove(tmp)
