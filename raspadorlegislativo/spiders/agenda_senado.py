import re
from datetime import date, datetime, timedelta

from scrapy import Request, Spider
from pytz import timezone

from raspadorlegislativo.items import Event
from raspadorlegislativo.spiders.senado import SenadoSpider


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

    @staticmethod
    def parse_items(event):
        for item in event.xpath('Partes/Parte/Itens/Item/Nome/text()'):
            yild
