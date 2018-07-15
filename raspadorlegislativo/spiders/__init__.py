import os
from collections import namedtuple
from contextlib import contextmanager
from json import JSONDecodeError
from tempfile import mkstemp

from PyPDF2 import PdfFileReader
from requests import post
from scrapy import Spider as OriginalSpider

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill


PendingRequest = namedtuple(
    'PendingRequest',
    ('request_class', 'url', 'callback')
)


class Spider(OriginalSpider):

    def close(self, spider):
        data = {
            'token': settings.RASPADOR_API_TOKEN,
            'start_time': spider.crawler.stats.get_value('start_time'),
            'origem': 'CA' if self.name == 'camara' else 'SE'
        }
        url = f'{settings.RASPADOR_API_URL}fim-da-raspagem/'
        response = post(url, data=data)

        try:
            content = response.json()
        except JSONDecodeError:
            content = response.text

        spider.logger.info(content)

    def process_pending_requests_or_yield_item(self, bill, pending_requests):
        if pending_requests:
            next_request, *pending_requests = pending_requests
            yield next_request.request_class(
                url=next_request.url,
                meta={'bill': bill, 'pending_requests': pending_requests},
                callback=next_request.callback
            )
        elif bill['palavras_chave']:
            yield Bill(bill)

    def parse_pdf(self, response):
        with self.text_from_pdf(response.body) as text:
            text = text.lower()
            for keyword in (k for k in settings.KEYWORDS if k in text):
                response.meta['bill']['palavras_chave'].add(keyword)

        args = (response.meta['bill'], response.meta['pending_requests'])
        yield from self.process_pending_requests_or_yield_item(*args)

    @contextmanager
    def text_from_pdf(self, pdf_in_bytes):
        _, tmp = mkstemp(suffix='.pdf')

        with open(tmp, 'wb') as fobj:
            fobj.write(pdf_in_bytes)

        with open(tmp, 'rb') as fobj:
            pdf = PdfFileReader(fobj)
            contents = '\n'.join(
                pdf.getPage(num).extractText()
                for num in range(pdf.numPages)
            )

        yield contents
        os.remove(tmp)
