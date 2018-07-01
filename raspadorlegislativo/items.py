# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Bill(scrapy.Item):
    nome = scrapy.Field()
    id_site = scrapy.Field()
    apresentacao = scrapy.Field()
    ementa = scrapy.Field()
    url = scrapy.Field()
    match = scrapy.Field()
