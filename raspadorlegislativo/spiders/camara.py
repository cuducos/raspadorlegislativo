import json

from scrapy import Request

from raspadorlegislativo import settings
from raspadorlegislativo.spiders import PendingRequest, Spider
from raspadorlegislativo.utils.feed import feed
from raspadorlegislativo.utils.requests import JsonRequest


class CamaraSpider(Spider):
    name = 'camara'
    subjects = ('PL',)
    custom_settings = {'FEED_URI': feed('camara')}
    urls = {
        'list': 'https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo={}&dataInicio={}',
        'human': 'http://www.camara.gov.br/proposicoesWeb/fichadetramitacao?idProposicao={}'
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
        uuid = self.get_unique_id()
        data = {
            'palavras_chave': set(),  # include matching keywords in this list
            'nome': '{} {}'.format(bill.get('siglaTipo'), bill.get('numero')),
            'id_site': bill.get('id'),
            'apresentacao': bill.get('dataApresentacao')[:10],  # 10 chars date
            'ementa': bill.get('ementa'),
            'origem': 'CA',
            'url': self.urls['human'].format(bill.get('id')),
            'pending_requests': [
                PendingRequest(
                    JsonRequest,
                    bill.get('uri'),
                    'parse_bill_authorship'
                ),
                PendingRequest(
                    JsonRequest,
                    bill.get('statusProposicao', {}).get('uriOrgao'),
                    'parse_bill_local'
                ),
                PendingRequest(
                    Request,
                    bill.get('urlInteiroTeor'),
                    'parse_pdf'
                )
            ]
        }

        summary = ' '.join((data['ementa'], bill.get('keywords')))
        for keyword in settings.KEYWORDS:
            if keyword in summary.lower():
                data['palavras_chave'].add(keyword)

        self.set_bill(uuid, data)
        yield from self.process_pending_requests(uuid)

    def parse_bill_authorship(self, uuid, response):
        """Parser para processar a página que tem detalhes sobre a autoria de
        um dado PL. Esse método encerra chamando um outro método para obter os
        detalhes sobre o local de tramitação do PL."""
        authorship = json.loads(response.body_as_unicode()).get('dados')
        data = self.get_bill(uuid)
        data['autoria'] = ', '.join(a.get('nome') for a in authorship)
        self.set_bill(uuid, data)

    def parse_bill_local(self, uuid, response):
        """Parser para processar a página com detalhes do local de tramitação
        de um dado PL. Esse método pode ou iniciar uma nova requisição para
        buscar o PDF com o texto completo do PL, ou, caso alguma das palavras
        chaves seja encontrada nos metadados dos PL (ementa, por exemplo), já
        retorna um objeto (dicionário) com os dados do PL se necessitar de nova
        requisição."""
        local = json.loads(response.body_as_unicode()).get('dados', {})
        data = self.get_bill(uuid)
        data['local'] = local.get('nome')
        self.set_bill(uuid, data)
