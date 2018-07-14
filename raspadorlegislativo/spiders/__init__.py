import os
from collections import namedtuple
from functools import partial
from tempfile import mkstemp
from uuid import uuid4

from scrapy import Spider as OriginalSpider
from memcache import Client

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill
from raspadorlegislativo.utils.pdf import extract_text


PendingRequest = namedtuple('PendingRequest', ('request', 'url', 'callback'))


class Spider(OriginalSpider):

    def __init__(self):
        self.cache = Client((settings.MEMCACHED_LOCATION,))

    def get_unique_id(self):
        return str(uuid4()).encode()

    def set_bill(self, uuid, data):
        return self.cache.set(uuid, data, 60 * 60 * 3)

    def get_bill(self, uuid):
        return self.cache.get(uuid)

    def has_pending_request(self, uuid):
        data = self.get_bill(uuid)
        return bool(data.get('pending_requests'))

    def process_pending_requests(self, uuid):
        data = self.get_bill(uuid)
        while self.has_pending_request(uuid):
            next_request, *pending_requests = data['pending_requests']
            data['pending_requests'] = pending_requests
            self.set_bill(uuid, data)

            yield next_request.request(
                url=next_request.url,
                callback=partial(getattr(self, next_request.callback), uuid)
            )

            data = self.get_bill(uuid)

        if data['palavras_chave']:
            data.pop('pending_requests')
            yield Bill(data)

    def parse_pdf(self, uuid, response):
        _, tmp = mkstemp(suffix='.pdf')
        with open(tmp, 'wb') as fobj:
            fobj.write(response.body)
        text = extract_text(tmp).lower()

        data = self.get_bill(uuid)
        for keyword in settings.KEYWORDS:
            if keyword in text:
                data['palavras_chave'].add(keyword)

        os.remove(tmp)
        self.set_bill(uuid, data)
