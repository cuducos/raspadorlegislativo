import os
from tempfile import mkstemp

from scrapy import Spider

from raspadorlegislativo import settings
from raspadorlegislativo.utils.pdf import extract_text


class Spider(Spider):

    def parse_pdf(self, data, response):
        _, tmp = mkstemp(suffix='.pdf')
        with open(tmp, 'wb') as fobj:
            fobj.write(response.body)

        text = extract_text(tmp).lower()
        for keyword in settings.KEYWORDS:
            if keyword in text:
                yield data
                break  # we don't need to collect the same item twice

        os.remove(tmp)
