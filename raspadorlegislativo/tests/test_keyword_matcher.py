from raspadorlegislativo.matchers import Matcher


RULES = {
    'name': 'Penal Econômico',
    'keywords': ['corrupção', 'lavagem de dinheiro'],
    'exclude': ['corrupção de menores'],
    'combined_keywords': [['rede social', 'crime']]
}


def test_simple_match():
    data = RULES.copy()
    data.pop('exclude')
    data.pop('combined_keywords')
    matcher = Matcher(data)
    assert matcher.match('tchau Corrupção') == (True, ('corrupção',))
    assert matcher.match('oi mundo') == (False, tuple())


def test_match_with_excude():
    data = RULES.copy()
    data.pop('combined_keywords')
    matcher = Matcher(data)
    assert matcher.match('tchau Corrupção') == (True, ('corrupção',))
    assert matcher.match('e Corrupção de menores') == (False, ('corrupção',))


def test_match_with_combined_keywords():
    data = RULES.copy()
    matcher = Matcher(data)
    matched, matches = matcher.match('tchau crime na rede social')
    assert matched
    assert matches == ('rede social', 'crime')
