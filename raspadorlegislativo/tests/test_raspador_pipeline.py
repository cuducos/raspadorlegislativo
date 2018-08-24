from urllib.parse import urlencode
from urllib.request import Request

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill
from raspadorlegislativo.pipelines import RaspadorlegislativoPipeline


item = Bill(
    nome='PL 3.1415',
    id_site='31415',
    apresentacao='2018-01-01',
    ementa='Foobar',
    autoria='Fulana de Tal',
    local='Câmara',
    origem='CA',
    url='https://foob.ar/',
    palavras_chave=('key', 'word'),
    palavras_chave_originais='keyword, whatever'
)

serialized = {
    'nome': 'PL 3.1415',
    'id_site': '31415',
    'apresentacao': '2018-01-01',
    'ementa': 'Foobar',
    'autoria': 'Fulana de Tal',
    'local': 'Câmara',
    'origem': 'CA',
    'url': 'https://foob.ar/',
    'palavras_chave': 'key, word',
    'palavras_chave_originais': 'keyword, whatever',
    'token': settings.RASPADOR_API_TOKEN
}


def test_serialize():
    pipeline = RaspadorlegislativoPipeline()
    assert urlencode(serialized).encode('ascii') == pipeline.serialize(item)


def test_process_item(mocker):
    endpoint = mocker.patch.object(RaspadorlegislativoPipeline, 'endpoint')
    endpoint.return_value = 'https://radarlegislativo.org/api/projetos'
    urlopen = mocker.patch('raspadorlegislativo.pipelines.urlopen')
    request = mocker.patch('raspadorlegislativo.pipelines.Request')
    post = mocker.patch.object(RaspadorlegislativoPipeline, 'should_post')
    post.return_value = True

    pipeline = RaspadorlegislativoPipeline()
    pipeline.process_item(item, mocker.Mock())
    request.assert_called_once_with(
        'https://radarlegislativo.org/api/projetos',
        data=urlencode(serialized).encode('ascii')
    )
    urlopen.assert_called_once_with(request.return_value)
