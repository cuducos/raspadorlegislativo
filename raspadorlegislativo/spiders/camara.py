import json

from scrapy import Request

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill
from raspadorlegislativo.requests import JsonRequest
from raspadorlegislativo.spiders import Spider


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
        """Parser p/ página que lista todos os PLs da Câmara"""
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
        """Parser p/ página do PL. Encadeia o parser da página de autoria."""
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
        urls = {
            'local': bill.get('statusProposicao', {}).get('uriOrgao'),
            'pdf': bill.get('urlInteiroTeor')
        }

        summary = ' '.join(
            text.lower() for text in (data['ementa'], bill.get('keywords'))
            if text
        )
        for keyword in settings.KEYWORDS:
            if keyword in summary:
                data['palavras_chave'].add(keyword)

        meta = {'bill': data, 'urls': urls}
        url = bill.get('uriAutores')
        yield JsonRequest(url, self.parse_authorship, meta=meta)

    def parse_authorship(self, response):
        """Parser p/ página de autoria. Encadeia parser p/ página de local."""
        data = json.loads(response.body_as_unicode())
        authorship = (author.get('nome') for author in data.get('dados'))
        response.meta['bill']['autoria'] = ', '.join(authorship)

        url = response.meta['urls'].pop('local')
        meta = {'bill': response.meta['bill'], 'urls': response.meta['urls']}
        yield JsonRequest(url, self.parse_local, meta=meta)

    def parse_local(self, response):
        """Parser p/ página de local. Encadeia parser p/ inteiro teor."""
        local = json.loads(response.body_as_unicode()).get('dados', {})
        response.meta['bill']['local'] = local.get('nome')

        url = response.meta['urls'].pop('pdf')
        meta = {'bill': response.meta['bill']}
        yield Request(url, self.parse_pdf, meta=meta)

    def parse_pdf(self, response):
        """Parser p/ PDF inteiro teor."""
        with self.text_from_pdf(response.body) as text:
            text = text.lower()
            for keyword in (k for k in settings.KEYWORDS if k in text):
                response.meta['bill']['palavras_chave'].add(keyword)

        yield Bill(response.meta['bill'])
