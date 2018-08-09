import re
from datetime import date, datetime, timedelta

from scrapy import Request, Spider
from pytz import timezone

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill, Event
from raspadorlegislativo.spiders import BillSpider


class SenadoSpider(BillSpider):
    """Raspa os dados da lista de todas as matérias que estão tramitando no
    Senado, filtradas por Projeto de Lei no Senado."""

    name = 'senado'
    subjects = ('PLS', 'PLC', 'PEC')
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
        with self.text_from_pdf(response) as text:
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


class AgendaSenadoSpider(Spider):
    name = 'agenda_senado'
    allowed_domains = ('legis.senado.leg.br',)
    url = 'http://legis.senado.leg.br/dadosabertos/agenda/{}/{}/detalhe'

    def start_requests(self):
        end = date.today() + timedelta(days=30)
        start = date.today() - timedelta(days=30)
        interval = (d.strftime('%Y%m%d') for d in (start, end))
        yield Request(self.url.format(*interval))

    def parse(self, response):
        """Parser para página que lista todos os eventos do Senado"""
        for event in response.xpath('Reuniao'):
            if self.is_related_to_a_bill(event):
                yield Event(
                    id_site=event.xpath('Codigo/text()').extract_first(),
                    data=self.parse_date(event),
                    descricao=self.parse_description(event),
                    local=event.xpath('Comissoes/Comissao/Nome/text()').extract_first()                )

    @staticmethod
    def is_related_to_a_bill(event):
        for subject in SenadoSpider.subjects:
            if re.findall(r'{} ?\d+'.format(subject), event.extract()):
                return True
        return False

    @staticmethod
    def parse_date(event):
        date_ = event.xpath('Data/text()').extract_first()
        time_ = event.xpath('Hora/text()').extract_first()
        result = datetime.strptime(f'{date_} {time_}', '%d/%m/%Y %H:%M')
        return result.replace(tzinfo=timezone('America/Sao_Paulo'))

    def parse_description(self, event):
        objective = event.xpath('Partes/Parte/Finalidade/text()').extract_first() or ''
        if objective:
            objective = f'**Finalidade**\n{objective}'

        ps = event.xpath('Partes/Parte/Eventos/Evento/Observacoes/text()').extract_first() or ''
        if ps:
            ps = f'**Observações**\n{ps}'

        invitees = tuple(self.parse_invitees(event)) or ''
        if invitees:
            invitee_list = '\n'.join(invitees)
            invitees = f'**Convidados**\n\n{invitee_list}'

        items = ', '.join(event.xpath('Partes/Parte/Itens/Item/Nome/text()').extract())
        if items:
            items = f'**Pauta**\n {items}'

        contents = (text for text in (objective, items, ps, invitees) if text)
        return '\n\n'.join(contents)

    @staticmethod
    def parse_invitees(event):
        for invitee in event.xpath('Partes/Parte/Eventos/Convidados/Convidado'):
            name = invitee.xpath('Nome/text()').extract_first()
            title = invitee.xpath('Cargo/text()').extract_first()
            yield f'* {name} ({title})'
