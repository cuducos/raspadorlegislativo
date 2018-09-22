import os
import re
from json import load


class Matcher:

    def __init__(self, data):
        """The argument `data` should be an object (converted into a
        dictionary) as each element of the array from
        `secrets/keywords.json.sample`, that is to say, it must contain the
        keywords `name` and `keywords` and optionally the keywords `exclude`
        and `combined_keywords`"""
        self.name = data['name']
        self.keywords = set(word.lower() for word in data['keywords'])
        self.exclude = set(
            word.lower()
            for word in data.get('exclude', tuple())
        )
        self.combined_keywords = set(
            tuple(word.lower() for word in group)
            for group in data.get('combined_keywords', tuple())
        )

    def _matches(self, text):
        """Returns the keywords and combined keywords found in `text`"""
        for word in self.keywords:
            pattern = f'(\\W{word}\\W)|(^{word}\\W)|(\\W{word}$)'
            matches = re.findall(pattern, text)
            if matches:
                yield word

        for group in self.combined_keywords:
            matches = tuple(word in text for word in group)
            if all(matches):
                yield from group

    def match(self, text):
        """Given a `text` (as string) returns a tuple. The first item is a
        boolean representing if this text matches the rules, and the second
        item is a tuple with the keywords that match. The rules are:

        1. at least one word/expression from `self.keywords` must be present in
           `text`
        2. if `self.combined_keywords` is not empty at least one group of
           words/expressions from `self.combined_keywords` must be present in
           `text`
        3. even if the previous rules are true, it will still return `False`
           if any word/expression in `self.exclude` is present in `text`"""
        text = text.lower() if text else ''

        matches = tuple(self._matches(text))
        if not matches:
            return False, matches

        for word in self.exclude:
            if word in text:
                return False, matches

        return True, matches


def keyword_matcher_parser(path):
    if not path or not os.path.exists(path) or not os.path.isfile(path):
        return tuple()

    with open(path) as fobj:
        configs = load(fobj)
        return tuple(Matcher(data) for data in configs)
