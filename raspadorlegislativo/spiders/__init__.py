import os
from contextlib import contextmanager
from json import JSONDecodeError
from tempfile import mkstemp

from PyPDF2 import PdfFileReader
from requests import post
from scrapy import Spider as OriginalSpider

from raspadorlegislativo import settings


class Spider(OriginalSpider):

    def close(self, spider):
        if not all((settings.RASPADOR_API_TOKEN, settings.RASPADOR_API_URL)):
            return

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
