import json
from functools import partial

from scrapy import Request

from raspadorlegislativo import settings
from raspadorlegislativo.spiders import Spider
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
        data = {
            'nome': '{} {}'.format(bill.get('siglaTipo'), bill.get('numero')),
            'id_site': bill.get('id'),
            'apresentacao': bill.get('dataApresentacao')[:10],  # 10 chars date
            'ementa': bill.get('ementa'),
            'url': self.urls['human'].format(bill.get('id')),
            'extra': {
                'keywords': bill.get('keywords'),
                'local_url': bill.get('statusProposicao', {}).get('uriOrgao'),
                'pdf_url': bill.get('urlInteiroTeor')
            }
        }

        yield JsonRequest(
            url=bill.get('uriAutores'),
            callback=partial(self.parse_bill_authorship, data)
        )

    def parse_bill_authorship(self, data, response):
        """Parser para processar a página que tem detalhes sobre a autoria de
        um dado PL. Esse método encerra chamando um outro método para obter os
        detalhes sobre o local de tramitação do PL."""
        authorship = json.loads(response.body_as_unicode()).get('dados')
        data['autoria'] = ', '.join(a.get('nome') for a in authorship)

        yield JsonRequest(
            url=data['extra']['local_url'],
            callback=partial(self.parse_bill_local, data)
        )

    def parse_bill_local(self, data, response):
        """Parser para processar a página com detalhes do local de tramitação
        de um dado PL. Esse método pode ou iniciar uma nova requisição para
        buscar o PDF com o texto completo do PL, ou, caso alguma das palavras
        chaves seja encontrada nos metadados dos PL (ementa, por exemplo), já
        retorna um objeto (dicionário) com os dados do PL se necessitar de nova
        requisição."""
        local = json.loads(response.body_as_unicode()).get('dados')
        data['local'] = local.get('nome')

        pdf_url = data['extra']['pdf_url']
        summary = ' '.join((data['ementa'], data['extra']['keywords']))
        data.pop('extra')

        for keyword in settings.KEYWORDS:
            if keyword in summary.lower():
                yield data
                break
        else:
            yield Request(
                url=pdf_url,
                callback=partial(self.parse_pdf, data)
            )
