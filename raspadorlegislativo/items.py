from scrapy import Field, Item


class Bill(Item):
    nome = Field()
    id_site = Field()
    apresentacao = Field()
    ementa = Field()
    autoria = Field()
    local = Field()
    origem = Field()

    url = Field()
    match = Field()
