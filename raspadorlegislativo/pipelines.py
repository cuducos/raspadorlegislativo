import logging

from requests import post

from raspadorlegislativo.items import Bill, Event
from raspadorlegislativo.settings import RASPADOR_API_TOKEN, RASPADOR_API_URL


log = logging.getLogger(__name__)


class RaspadorlegislativoPipeline:

    def process_item(self, item, spider):
        if all((RASPADOR_API_TOKEN, RASPADOR_API_URL)):
            self.post(item)

        return item

    def post(self, item):
        response = post(self.endpoint(item), data=self.serialize(item))
        if response.status_code != 201:
            log.info(f'{item._class.__name__} not saved via API')
            log.info(response.status_code)
            log.info(response.text)
            return

        log.info(f'{item._class.__name__} saved via API')

    def serialize(self, item):
        data = dict(item)
        data['token'] = RASPADOR_API_TOKEN

        if isinstance(item, Bill):
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
