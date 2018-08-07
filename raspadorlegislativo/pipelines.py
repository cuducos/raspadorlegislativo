from scrapy import FormRequest

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
                f'{RASPADOR_API_URL}projeto/',
                formdata=self.serialize(item),
                callback=lambda resp: None
            )
            self.crawler.engine.crawl(request, spider)

        return item

    def serialize(self, item):
        data = dict(item)
        data.pop('inteiro_teor')
        data['token'] = RASPADOR_API_TOKEN
        data['palavras_chave'] = ', '.join(data['palavras_chave'])
        return data
