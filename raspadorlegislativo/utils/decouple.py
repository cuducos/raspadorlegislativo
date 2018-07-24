import os
from json import load


def keyword_parser(path):
    if not path or not os.path.exists(path):
        return set()

    with open(path) as fobj:
        data = load(fobj)

    return set(keyword for keywords in data.values() for keyword in keywords)
