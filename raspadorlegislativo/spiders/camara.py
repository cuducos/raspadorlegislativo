import json

from scrapy import Request

from raspadorlegislativo import settings
from raspadorlegislativo.spiders import PendingRequest, Spider
from raspadorlegislativo.requests import JsonRequest


class CamaraSpider(Spider):
    """Raspa os dados da lista de todas as matérias que estão tramitando na
    Câmara, filtradas por Projeto de Lei."""

    name = 'camara'
    subjects = ('PL',)
    urls = {
        'list': (
            'https://dadosabertos.camara.leg.br/'
            'api/v2/proposicoes?siglaTipo={}&dataInicio={}'
        ),
        'human': (
            'http://www.camara.gov.br/'
            'proposicoesWeb/fichadetramitacao?idProposicao={}'
        )
    }

    def start_requests(self):
        for subject in self.subjects:
            url = self.urls['list'].format(subject, settings.START_DATE)
            yield JsonRequest(url)

    def parse(self, response):
        """Parser para página que lista todos os PLs da Câmara"""
        contents = json.loads(response.body_as_unicode())
        bills = contents.get('dados', tuple())
        links = contents.get('links', tuple())

        for bill in bills:
            yield JsonRequest(bill.get('uri'), self.parse_bill)

        for link in links:
            if link.get('rel') == 'next':
                yield JsonRequest(link.get('href'))
                break

    def parse_bill(self, response):
        bill = json.loads(response.body_as_unicode()).get('dados', {})
        data = {
            'palavras_chave': set(),  # include matching keywords in this list
            'nome': '{} {}'.format(bill.get('siglaTipo'), bill.get('numero')),
            'id_site': bill.get('id'),
            'apresentacao': bill.get('dataApresentacao')[:10],  # 10 chars date
            'ementa': bill.get('ementa'),
            'origem': 'CA',
            'url': self.urls['human'].format(bill.get('id'))
        }
        requests = [
            PendingRequest(
                JsonRequest,
                bill.get('uri'),
                self.parse_authorship
            ),
            PendingRequest(
                JsonRequest,
                bill.get('statusProposicao', {}).get('uriOrgao'),
                self.parse_local
            ),
            PendingRequest(
                Request,
                bill.get('urlInteiroTeor'),
                self.parse_pdf
            )
        ]

        summary = ' '.join(
            text.lower() for text in (data['ementa'], bill.get('keywords'))
            if text
        )
        for keyword in settings.KEYWORDS:
            if keyword in summary:
                data['palavras_chave'].add(keyword)

        yield from self.process_pending_requests_or_yield_item(data, requests)

    def parse_authorship(self, response):
        data = json.loads(response.body_as_unicode())
        authorship = (author.get('nome') for author in data.get('dados'))
        response.meta['bill']['autoria'] = ', '.join(authorship)

        args = (response.meta['bill'], response.meta['pending_requests'])
        yield from self.process_pending_requests_or_yield_item(*args)

    def parse_local(self, response):
        local = json.loads(response.body_as_unicode()).get('dados', {})
        response.meta['bill']['local'] = local.get('nome')

        args = (response.meta['bill'], response.meta['pending_requests'])
        yield from self.process_pending_requests_or_yield_item(*args)
