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
        data = self.serialize(item)
        response = post(settings.RASPADOR_API_URL, data=data)
        if response.status_code == 201:
            log.info('Bill saved via API')

        else:
            log.info('Bill not saved via API')
            log.info(response.status_code)
            log.info(response.text)

    def serialize(self, item):
        data = dict(item)
        data['token'] = settings.RASPADOR_API_TOKEN
        data['palavras_chave'] = ', '.join(data['palavras_chave'])
        return data
