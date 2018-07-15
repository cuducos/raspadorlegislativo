from scrapy import Request

from raspadorlegislativo import settings
from raspadorlegislativo.spiders import PendingRequest, Spider


class SenadoSpider(Spider):
    """Raspa os dados da lista de todas as matérias que estão tramitando no
    Senado, filtradas por Projeto de Lei no Senado."""

    name = 'senado'
    allowed_domains = ('legis.senado.leg.br',)
    subjects = ('PLS',)
    urls = {
        'list': (
            'http://legis.senado.leg.br/'
            'dadosabertos/materia/tramitando?sigla={}&data={}'
        ),
        'detail':  'http://legis.senado.leg.br/dadosabertos/materia/{}',
        'texts': 'http://legis.senado.leg.br/dadosabertos/materia/textos/{}',
        'humans': (
            'https://www25.senado.leg.br/'
            'web/atividade/materias/-/materia/{}'
        )
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
                meta={'code': code},
                callback=self.parse_bill
            )

    def parse_bill(self, response):
        description = response.xpath('//EmentaMateria/text()').extract_first()
        keywords = response.xpath('//IndexacaoMateria/text()').extract_first()
        number = response.xpath('//NumeroMateria/text()').extract_first()
        subject = response.xpath('//SiglaSubtipoMateria/text()').extract_first()

        data = {
            'palavras_chave': set(),  # include matching keywords in this list
            'nome': f'{subject} {number}',
            'id_site': response.xpath('//CodigoMateria/text()').extract_first(),
            'apresentacao': response.xpath('//DataApresentacao/text()').extract_first(),
            'ementa': description,
            'autoria': response.xpath('//NomeAutor/text()').extract_first(),
            'local': response.xpath('//NomeLocal/text()').extract_first(),
            'origem': 'SE',
            'url': self.urls['humans'].format(response.meta['code'])
        }

        requests = [
            PendingRequest(
                Request,
                self.urls['texts'].format(response.meta['code']),
                self.parse_texts
            )
        ]

        summary = ' '.join(
            text.lower() for text in (description, keywords)
            if text
        )
        for keyword in settings.KEYWORDS:
            if keyword in summary:
                data['palavras_chave'].add(keyword)

        yield from self.process_pending_requests_or_yield_item(data, requests)

    def parse_texts(self, response):
        for text in response.xpath('//Text'):
            file_type = text.xpath('//TipoDocumento/text()').extract_first()
            if file_type.lower() == 'pdf':
                new_request = PendingRequest(
                    Request,
                    text.xpath('//UrlTexto/text()').extract_first(),
                    self.parse_pdf
                )
                response.meta['pending_requests'].append(new_request)

        args = (response.meta['bill'], response.meta['pending_requests'])
        yield from self.process_pending_requests_or_yield_item(*args)
