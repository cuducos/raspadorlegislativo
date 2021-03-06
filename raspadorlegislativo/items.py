from scrapy import Field, Item


class Bill(Item):
    nome = Field()
    id_site = Field()
    apresentacao = Field()
    ementa = Field()
    autoria = Field()
    autoria_ids = Field()
    local = Field()
    origem = Field()
    palavras_chave = Field()
    palavras_chave_originais = Field()
    url = Field()


class Event(Item):
    id_site = Field()
    data = Field()
    local = Field()
    descricao = Field()
    origem = Field()
