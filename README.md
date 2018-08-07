# Raspador Legislativo

Repositório de testes de código para integrar, futuramente, o
[Radar Legislativo](https://gitlab.com/codingrights/radarlegislativo). O
objetivo é automatizar a inclusão de projetos de lei e aganda de tramitação no
_Radar_ de acordo com palavras chaves.

## Configurações

Copie os arquivos de configuração e edite-os de acordo com o desejado:

```sh
$ cp .env.sample .env
$ cp secrets/keywords.json.sample secrets/keywords.json
```

### Coletando todos os projetos de lei

Não configurar a variável `KEYWORDS` faz com que o _Raspador_ colete dados
sobre **todos** os projetos de lei em tramitação desde `START_DATE`, mas
nesse caso o _Raspador_ **não** envia os resultados para a API do
_Radar Legislativo_.

### Enviando os dados para o _Radar Legislativo_

Configurando as variáveis `RASPADOR_API_URL` e `RASPADOR_API_TOKEN` de acordo
com sua instância do _Radar Legislativo_ faz com que os projetos de lei
encontrados sejam enviados para o _Radar_ **desde que** houver ao menos uma
palavra-chave configurada no arquivo configurado na variávem de ambiente
`KEYWORDS`.

## Instalação em container (com Docker)

Requer [Docker](https://docs.docker.com/install/) e
[Docker Compose](https://docs.docker.com/compose/install/).

Para rodar todos os raspadores:

```sh
$ docker-compose run --rm scrapy python run.py
```

Ou, para rodar um em específico:

```sh
$ docker-compose run --rm scrapy scrapy crawl <nome do raspador>
```

Verifique o resultado no diretótio `data/` (ou, se for o caso, na sua instância
do _Radar Legislativo_).

### Testes

```sh
docker-compose run --rm scrapy py.test
```

## Instalação local (sem Docker)

Requer [Python](https://python.org) 3.6 com [Pipenv](https://docs.pipenv.org/).

Instale as dependências e entre no _virtualenv_:

```sh
$ pipenv install
$ pipenv shell
```

Para rodar todos os raspadores:

```sh
$ python run.py
```

Ou, para rodar um em específico:

```sh
$ scrapy crawl <nome do raspador>
```

Verifique o resultado no diretótio `data/` (ou, se for o caso, na sua instância
do _Radar Legislativo_).

### Testes

```sh
py.test
```