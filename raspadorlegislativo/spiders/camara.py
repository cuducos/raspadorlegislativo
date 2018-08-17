import json
import re
from datetime import datetime

from markdownify import markdownify
from scrapy import Request, Spider
from pytz import timezone

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill, Event
from raspadorlegislativo.requests import JsonRequest
from raspadorlegislativo.spiders import BillSpider


class CamaraMixin:

    def request_all_remaining_pages(self, response):
        contents = json.loads(response.body_as_unicode())
        links = contents.get('links', tuple())
        pattern = r'pagina=(?P<last>\d+)'
        for link in links:
            if link.get('rel') == 'last':
                url = link.get('href')
                match = re.search(pattern, url)
                last = int(match.group('last'))
                urls = (
                    re.sub(pattern, f'pagina={page}', url)
                    for page in range(1, last + 1)
                )
                yield from (JsonRequest(url) for url in urls)


class CamaraSpider(BillSpider, CamaraMixin):
    """Raspa os dados da lista de todas as matérias que estão tramitando na
    Câmara, filtradas por Projeto de Lei."""

    name = 'camara'
    subjects = ('PL', 'PLS', 'PEC')
    urls = {
        'list': (
            'https://dadosabertos.camara.leg.br/'
            'api/v2/proposicoes?siglaTipo={}&dataInicio={}&itens=100'
        ),
        'human': (
            'http://www.camara.gov.br/'
            'proposicoesWeb/fichadetramitacao?idProposicao={}'
        )
    }

    def start_requests(self):
        for subject in self.subjects:
            url = self.urls['list'].format(subject, settings.START_DATE)
            yield JsonRequest(url, meta={'is_first': True})

    def parse(self, response):
        """Parser p/ página que lista todos os PLs da Câmara"""
        contents = json.loads(response.body_as_unicode())
        bills = contents.get('dados', tuple())

        for bill in bills:
            yield JsonRequest(bill.get('uri'), self.parse_bill)

        if 'is_first' in response.meta:
            yield from self.request_all_remaining_pages(response)

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

        meta = {'bill': data, 'urls': urls, 'keywords': bill['keywords']}
        url = bill.get('uriAutores')
        yield JsonRequest(url, self.parse_authorship, meta=meta)

    def parse_authorship(self, response):
        """Parser p/ página de autoria. Encadeia parser p/ página de local."""
        data = json.loads(response.body_as_unicode())
        authorship = (author.get('nome') for author in data.get('dados'))
        response.meta['bill']['autoria'] = ', '.join(authorship)

        url = response.meta['urls'].pop('local')
        meta = {
            k: v for k, v in response.meta.items()
            if k in {'bill', 'urls', 'keywords'}
        }
        yield JsonRequest(url, self.parse_local, meta=meta)

    def parse_local(self, response):
        """Parser p/ página de local. Encadeia parser p/ inteiro teor."""
        local = json.loads(response.body_as_unicode()).get('dados', {})
        response.meta['bill']['local'] = local.get('nome')

        url = response.meta['urls'].pop('pdf')
        meta = {
            k: v for k, v in response.meta.items()
            if k in {'bill', 'keywords'}
        }
        if url:
            yield Request(url, self.parse_pdf, meta=meta)
        else:
            yield self.item(meta)

    def parse_pdf(self, response):
        """Parser p/ PDF inteiro teor."""
        with self.text_from_pdf(response) as text:
            text = text.lower()
            for keyword in (k for k in settings.KEYWORDS if k in text):
                response.meta['bill']['palavras_chave'].add(keyword)

        yield self.item(response.meta)

    def item(self, meta):
        if not settings.KEYWORDS:
            meta['bill']['palavras_chave'] = meta['keywords']

        if not settings.KEYWORDS or meta['bill']['palavras_chave']:
            return Bill(meta['bill'])


class AgendaCamaraSpider(Spider, CamaraMixin):
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
        yield JsonRequest(self.urls['api'], meta={'is_first': True})

    def parse(self, response):
        """Parser para página que lista todos os eventos da Câmara"""
        contents = json.loads(response.body_as_unicode())
        for event in contents.get('dados', tuple()):
            yield Request(
                self.urls['details'].format(event['id']),
                callback=self.parse_details,
                meta={'event': event}
            )

        if 'is_first' in response.meta:
            yield from self.request_all_remaining_pages(response)

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
