import logging

from requests import post

from raspadorlegislativo import settings


log = logging.getLogger(__name__)


class RaspadorlegislativoPipeline:

    def process_item(self, item, spider):
        if all((settings.RASPADOR_API_TOKEN, settings.RASPADOR_API_URL)):
            self.post(item)

        return item

    def post(self, item):
        url = f'{settings.RASPADOR_API_URL}projeto/'
        response = post(url, data=self.serialize(item))
        if response.status_code != 201:
            log.info('Bill not saved via API')
            log.info(response.status_code)
            log.info(response.text)
            return

        log.info('Bill saved via API')

    def serialize(self, item):
        data = dict(item)
        data['token'] = settings.RASPADOR_API_TOKEN
        data['palavras_chave'] = ', '.join(data['palavras_chave'])
        return data
