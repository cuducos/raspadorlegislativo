from scrapy import Request

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill
from raspadorlegislativo.spiders import Spider


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
        """Parser para página que lista todos os PLS."""
        codes = response.xpath('//CodigoMateria/text()').extract()
        for code in codes:
            yield Request(
                url=self.urls['detail'].format(code),
                meta={'code': code},
                callback=self.parse_bill
            )

    def parse_bill(self, response):
        """Parser p/ página de detalhes do PLS. Encadeia parser dos textos."""
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
            'url': self.urls['humans'].format(response.meta['code']),
            'inteiro_teor': []
        }

        summary = ' '.join(
            text.lower() for text in (description, keywords)
            if text
        )
        for keyword in settings.KEYWORDS:
            if keyword in summary:
                data['palavras_chave'].add(keyword)

        url = self.urls['texts'].format(response.meta['code'])
        meta = {'bill': data, 'keywords': keywords}
        yield Request(url, self.parse_texts, meta=meta)

    def parse_texts(self, response):
        pending_texts = tuple(
            text.xpath('//UrlTexto/text()').extract_first()
            for text in response.xpath('//Text')
            if text.xpath('//TipoDocumento/text()').extract_first().lower == 'pdf'
        )
        yield self.next_pdf_or_item(response, pending_texts)

    def parse_pdf(self, response):
        with self.text_from_pdf(response.body) as text:
            response.meta['bill']['inteiro_teor'] = \
                response.meta['bill']['inteiro_teor'].append(text)
            text = text.lower()
            for keyword in (k for k in settings.KEYWORDS if k in text):
                response.meta['bill']['palavras_chave'].add(keyword)

        pending_texts = response.meta.get('urls')
        yield self.next_pdf_or_item(response, pending_texts)

    def next_pdf_or_item(self, response, pending_texts):
        item = response.meta['bill']

        if not pending_texts:
            if not settings.KEYWORDS and not item['palavras_chave']:
                item['palavras_chave'] = response.meta['keywords']

            if not settings.KEYWORDS or item['palavras_chave']:
                return Bill(item)

            return None

        url, *urls = pending_texts
        meta = {
            'bill': item,
            'urls': urls,
            'keywords': response.meta['keywords']
        }
        return Request(url, self.parse_pdf, meta=meta)
