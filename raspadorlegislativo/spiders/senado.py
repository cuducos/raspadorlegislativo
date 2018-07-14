from functools import partial

from scrapy import Request

from raspadorlegislativo import settings
from raspadorlegislativo.spiders import PendingRequest, Spider
from raspadorlegislativo.utils.feed import feed


class SenadoSpider(Spider):
    """Raspa os dados da lista de todas as matérias que estão tramitando no
    Senado, filtradas por Projeto de Lei no Senado."""

    name = 'senado'
    custom_settings = {'FEED_URI': feed('senado')}
    allowed_domains = ('legis.senado.leg.br',)
    subjects = ('PLS',)
    urls = {
        'list': 'http://legis.senado.leg.br/dadosabertos/materia/tramitando?sigla={}&data={}',
        'detail':  'http://legis.senado.leg.br/dadosabertos/materia/{}',
        'texts': 'http://legis.senado.leg.br/dadosabertos/materia/textos/{}',
        'humans': 'https://www25.senado.leg.br/web/atividade/materias/-/materia/{}'
    }

    def start_requests(self):
        for subject in self.subjects:
            start_date = settings.START_DATE.replace('-', '')
            url = self.urls['list'].format(subject, start_date)
            yield Request(url=url)

    def parse(self, response):
        codes = response.xpath('//CodigoMateria/text()').extract()
        for code in codes:
            yield Request(
                url=self.urls['detail'].format(code),
                callback=partial(self.parse_subject, code)
            )

    def parse_subject(self, code, response):
        description = response.xpath('//EmentaMateria/text()').extract_first() or ''
        keywords = response.xpath('//IndexacaoMateria/text()').extract_first() or ''
        number = response.xpath('//NumeroMateria/text()').extract_first()
        subject = response.xpath('//SiglaSubtipoMateria/text()').extract_first()

        uuid = self.get_unique_id()
        data = {
            'palavras_chave': set(),  # include matching keywords in this list
            'nome': f'{subject} {number}',
            'id_site': response.xpath('//CodigoMateria/text()').extract_first(),
            'apresentacao': response.xpath('//DataApresentacao/text()').extract_first(),
            'ementa': description,
            'autoria': response.xpath('//NomeAutor/text()').extract_first(),
            'local': response.xpath('//NomeLocal/text()').extract_first(),
            'origem': 'SE',
            'url': self.urls['humans'].format(code),
            'pending_requests': [
                PendingRequest(
                    Request,
                    self.urls['texts'].format(code),
                    'parse_texts'
                )
            ]
        }

        summary = ' '.join((description, keywords))
        for keyword in settings.KEYWORDS:
            if keyword in summary.lower():
                data['palavras_chave'].add(keyword)

        import logging
        log = logging.getLogger(__name__)
        log.debug(data)
        self.set_bill(uuid, data)
        yield from self.process_pending_requests(uuid)

    def parse_texts(self, uuid, response):
        data = self.get_bill(uuid)

        for text in response.xpath('//Text'):
            file_type = text.xpath('//TipoDocumento/text()').extract()
            if file_type.lower() == 'pdf':
                request = PendingRequest(
                    Request,
                    text.xpath('//UrlTexto/text()').extract(),
                    self.parse_pdf
                )
                data['pending_requests'].append(request)

        self.set_bill(uuid, data)
