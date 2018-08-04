import json
import re
from datetime import datetime

from markdownify import markdownify
from scrapy import Request, Spider
from pytz import timezone

from raspadorlegislativo.items import Event
from raspadorlegislativo.spiders.camara import CamaraSpider
from raspadorlegislativo.utils.requests import JsonRequest


class AgendaCamaraSpider(Spider):
    name = 'agenda_camara'
    allowed_domains = ('camara.leg.br',)
    urls = {
        'api': 'https://dadosabertos.camara.leg.br/api/v2/eventos',
        'details': (
            'http://www.camara.leg.br/'
            'internet/ordemdodia/ordemDetalheReuniaoCom.asp?codReuniao={}'
        )
    }

    def start_requests(self):
        yield JsonRequest(self.urls['api'])

    def parse(self, response):
        """Parser para página que lista todos os eventos da Câmara"""
        contents = json.loads(response.body_as_unicode())
        for event in contents.get('dados', tuple()):
            yield Request(
                self.urls['details'].format(event['id']),
                callback=self.parse_details,
                meta={'event': event}
            )

        for link in contents.get('links', tuple()):
            if link.get('rel') == 'next':
                yield JsonRequest(url=link.get('href'))
                break

    def parse_details(self, response):
        """Parse para a página HTML com detalhes de um evento da agenda"""
        venues, venue = response.meta['event']['orgaos'], None
        for _venue in venues:
            for key in ('sigla', 'apelido'):
                for subject in CamaraSpider.subjects:
                    if re.findall(r'{} ?\d+'.format(subject), _venue[key]):
                        venue = _venue

        if venue:
            yield Event(
                id_site=response.meta['event']['id'],
                data=self.parse_date(response.meta['event']),
                descricao=self.parse_description(response),
                local=venue['nome']
            )

    @staticmethod
    def remove_node(context, css_selector):
        """Remove um nó do HTML com base em um seletor CSS"""
        for element in context.css(css_selector):
            element.root.getparent().remove(element.root)
        return context

    def parse_description(self, response):
        """Trata o texto da descrição com base no HTML de detalhe do evento"""
        *_, description = response.css('.caixaCOnteudo')

        # remove nós indesejados do HTML
        for selector in ('style', '.vejaTambem'):
            description = self.remove_node(description, selector)

        # remove caracteres indesejados do HTML
        description = description.extract()
        for char in ('\n', '\t', '\r'):
            description.replace(char, '')

        # remove espaços do início das linhas
        description = markdownify(description)
        return '\n'.join(line.strip() for line in description.split('\n'))

    @staticmethod
    def parse_date(event):
        naive = datetime.strptime(event['dataHoraInicio'], '%Y-%m-%dT%H:%M')
        return naive.replace(tzinfo=timezone('America/Sao_Paulo'))
