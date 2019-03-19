from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from raspadorlegislativo.items import Bill, Event
from raspadorlegislativo.settings import MATCHERS, RASPADOR_API_TOKEN, RASPADOR_API_URL


class RaspadorlegislativoPipeline:

    @staticmethod
    def should_post(item):
        should_post = all((MATCHERS, RASPADOR_API_TOKEN, RASPADOR_API_URL))
        if isinstance(item, Bill):  # only posts bills with matching keywords
            return should_post and bool(item.get('palavras_chave'))
        return should_post

    def process_item(self, item, spider):
        if self.should_post(item):
            try:
                urlopen(Request(self.endpoint(item), data=self.serialize(item)))
            except HTTPError as error:
                content = error.read()
                spider.logger.debug(f'[id_site={item["id_site"]} {content}')

        return item

    def serialize(self, item):
        data = dict(item)
        data['token'] = RASPADOR_API_TOKEN

        if 'palavras_chave' in data:
            if not isinstance(data['palavras_chave'], str):
                data['palavras_chave'] = ', '.join(data['palavras_chave'])

        return urlencode(data).encode('ascii')

    def endpoint(self, item):
        endpoint = None
        if isinstance(item, Bill):
            endpoint = 'projeto/'
        elif isinstance(item, Event):
            endpoint = 'evento/'

        if not endpoint:
            raise ValueError(f'No endpoint set for {item._class}')

        return f'{RASPADOR_API_URL}{endpoint}'
