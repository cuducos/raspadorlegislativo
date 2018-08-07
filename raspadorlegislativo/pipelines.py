from scrapy import FormRequest

from raspadorlegislativo.items import Bill, Event
from raspadorlegislativo.settings import KEYWORDS, RASPADOR_API_TOKEN, RASPADOR_API_URL


class RaspadorlegislativoPipeline:

    def __init__(self, crawler):
        self.crawler = crawler
        self.should_post = all((KEYWORDS, RASPADOR_API_TOKEN, RASPADOR_API_URL))

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_item(self, item, spider):
        if self.should_post and item['palavras_chave']:
            request = FormRequest(
                self.endpoint(item),
                formdata=self.serialize(item),
                callback=lambda resp: None
            )
            self.crawler.engine.crawl(request, spider)

        return item

    def serialize(self, item):
        data = dict(item)
        data['token'] = RASPADOR_API_TOKEN
        data.pop('inteiro_teor')

        if 'palavras_chave' in data:
            data['palavras_chave'] = ', '.join(data['palavras_chave'])

        return data

    def endpoint(self, item):
        endpoint = None
        if isinstance(item, Bill):
            endpoint = 'projeto/'
        elif isinstance(item, Event):
            endpoint = 'tramitacao/'

        if not endpoint:
            raise ValueError(f'No endpoint set for {item._class}')

        return f'{RASPADOR_API_URL}{endpoint}'
