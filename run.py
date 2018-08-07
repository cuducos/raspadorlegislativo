from scrapy.crawler import CrawlerProcess

from raspadorlegislativo.spiders.camara import AgendaCamaraSpider, CamaraSpider
from raspadorlegislativo.spiders.senado import AgendaSenadoSpider, SenadoSpider


spiders = (CamaraSpider, SenadoSpider, AgendaCamaraSpider, AgendaSenadoSpider)
process = CrawlerProcess()
for spider in spiders:
    process.crawl(spider)

process.start()
