import os
from contextlib import contextmanager
from tempfile import mkstemp

from PyPDF2 import PdfFileReader
from scrapy import Spider


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
