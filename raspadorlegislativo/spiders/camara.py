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
            yield JsonRequest(url=url)

    def parse(self, response):
        """Parser para página que lista todos os PLs da Câmara"""
        contents = json.loads(response.body_as_unicode())
        bills = contents.get('dados', tuple())
        links = contents.get('links', tuple())

        for bill in bills:
            yield JsonRequest(
                url=bill.get('uri'),
                callback=self.parse_bill_general
            )

        for link in links:
            if link.get('rel') == 'next':
                yield JsonRequest(url=link.get('href'))
                break

    def parse_bill_general(self, response):
        """1º passo do parser para página de detalhes de um PL da Câmara. Na
        sequência nova requisição é feita para buscar dados da autoria do
        PL e, na sequência, uma terceira para pegar os dados do local de
        tramitação."""
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
                self.parse_bill_authorship
            ),
            PendingRequest(
                JsonRequest,
                bill.get('statusProposicao', {}).get('uriOrgao'),
                self.parse_bill_local
            ),
            PendingRequest(
                Request,
                bill.get('urlInteiroTeor'),
                self.parse_pdf
            )
        ]

        summary = ' '.join((data['ementa'], bill.get('keywords')))
        for keyword in settings.KEYWORDS:
            if keyword in summary.lower():
                data['palavras_chave'].add(keyword)

        yield from self.process_pending_requests_or_yield_item(data, requests)

    def parse_bill_authorship(self, response):
        """Parser para processar a página que tem detalhes sobre a autoria de
        um dado PL. Esse método encerra chamando um outro método para obter os
        detalhes sobre o local de tramitação do PL."""
        data = json.loads(response.body_as_unicode())
        authorship = (author.get('nome') for author in data.get('dados'))
        response.meta['bill']['autoria'] = ', '.join(authorship)

        args = (response.meta['bill'], response.meta['pending_requests'])
        yield from self.process_pending_requests_or_yield_item(*args)

    def parse_bill_local(self, response):
        """Parser para processar a página com detalhes do local de tramitação
        de um dado PL. Esse método pode ou iniciar uma nova requisição para
        buscar o PDF com o texto completo do PL, ou, caso alguma das palavras
        chaves seja encontrada nos metadados dos PL (ementa, por exemplo), já
        retorna um objeto (dicionário) com os dados do PL se necessitar de nova
        requisição."""
        local = json.loads(response.body_as_unicode()).get('dados', {})
        response.meta['bill']['local'] = local.get('nome')

        args = (response.meta['bill'], response.meta['pending_requests'])
        yield from self.process_pending_requests_or_yield_item(*args)
