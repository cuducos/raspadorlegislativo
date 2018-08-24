import os
from contextlib import contextmanager
from tempfile import mkstemp

from PyPDF2 import PdfFileReader
from scrapy import Spider
from scrapy.spidermiddlewares.httperror import HttpError

from raspadorlegislativo import settings
from raspadorlegislativo.items import Bill


class BillSpider(Spider):

    @contextmanager
    def text_from_pdf(self, response):
        _, tmp = mkstemp(suffix='.pdf')

        with open(tmp, 'wb') as fobj:
            fobj.write(response.body)

        try:
            with open(tmp, 'rb') as fobj:
                pdf = PdfFileReader(fobj)
                contents = '\n'.join(
                    pdf.getPage(num).extractText()
                    for num in range(pdf.numPages)
                )
                yield contents
        except:
            self.logger.debug(f'Could not read the PDF for {response.url}')
            yield ''

        os.remove(tmp)

    @staticmethod
    def collect_keywords(bill, text):
        for matcher in settings.MATCHERS:
            matched, keywords = matcher.match(text)
            if matched:
                for keyword in keywords:
                    bill['palavras_chave'].add(keyword)
        return bill

    def error(self, failure):
        self.logger.error(repr(failure))
        if not failure.check(HttpError):
            return

        response = failure.value.response
        if 'bill' in response.meta:
            yield Bill(response.meta['bill'])
