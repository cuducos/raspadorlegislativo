import logging

from requests import post

from raspadorlegislativo.settings import RASPADOR_API_TOKEN, RASPADOR_API_URL


log = logging.getLogger(__name__)


class RaspadorlegislativoPipeline:

    credentials = all((RASPADOR_API_TOKEN, RASPADOR_API_URL))

    def process_item(self, item, spider):
        if self.credentials and item.palavras_chave:
            url = f'{RASPADOR_API_URL}projeto/'
            response = post(url, data=self.serialize(item))

            if response.status_code != 201:
                log.info('Bill not saved via API')
                log.info(response.status_code)
                log.info(response.text)

            log.info('Bill saved via API')

        return item

    def serialize(self, item):
        data = dict(item)
        data.pop('inteiro_teor')
        data['token'] = RASPADOR_API_TOKEN
        data['palavras_chave'] = ', '.join(data['palavras_chave'])
        return data
