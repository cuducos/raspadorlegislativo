import os
from collections import namedtuple
from json import JSONDecodeError
from tempfile import mkstemp

from scrapy import Spider as OriginalSpider
from requests import post

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill
from raspadorlegislativo.utils.pdf import extract_text


PendingRequest = namedtuple(
    'PendingRequest',
    ('request_class', 'url', 'callback')
)


class Spider(OriginalSpider):

    def origin(self):
        """Returns the field `origem` from Radar as a string"""
        mapping = dict(camara='CA', senado='SE')
        return mapping.get(self.name)

    def close(self, spider):
        data = {
            'token': settings.RASPADOR_API_TOKEN,
            'start_time': spider.crawler.stats.get_value('start_time'),
            'origem': spider.origin()
        }
        url = f'{settings.RASPADOR_API_URL}projeto/fim-da-raspagem/'
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
        else:
            yield Bill(bill)

    def parse_pdf(self, response):
        _, tmp = mkstemp(suffix='.pdf')
        with open(tmp, 'wb') as fobj:
            fobj.write(response.body)
        text = extract_text(tmp).lower()

        for keyword in settings.KEYWORDS:
            if keyword in text:
                response.meta['bill']['palavras_chave'].add(keyword)

        os.remove(tmp)
        args = (response.meta['bill'], response.meta['pending_requests'])
        yield from self.process_pending_requests_or_yield_item(*args)
