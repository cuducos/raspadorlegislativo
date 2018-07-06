from unittest.mock import Mock

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill
from raspadorlegislativo.pipelines import RaspadorlegislativoPipeline


pipeline = RaspadorlegislativoPipeline()

item = Bill(
    nome='PL 3.1415',
    id_site='31415',
    apresentacao='2018-01-01',
    ementa='Foobar',
    autoria='Fulana de Tal',
    local='Câmara',
    origem='CA',
    url='https://foob.ar/',
    match={'key', 'word'}
)

serialized = {
    'nome': 'PL 3.1415',
    'id_site': '31415',
    'apresentacao': '2018-01-01',
    'ementa': 'Foobar',
    'autoria': 'Fulana de Tal',
    'local': 'Câmara',
    'origem': 'CA',
    'token': settings.RASPADOR_API_TOKEN,
    'url': 'https://foob.ar/',
    'match': {'key', 'word'}
}


def test_serialize(mocker):
    assert serialized == pipeline.serialize(item)


def test_process_item(mocker):
    post = mocker.patch('raspadorlegislativo.pipelines.post')
    pipeline.process_item(item, Mock())
    post.assert_called_once_with(settings.RASPADOR_API_URL, data=serialized)
