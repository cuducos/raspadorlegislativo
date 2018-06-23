from scrapy import Request


class JsonRequest(Request):

    def __init__(self, *args, **kwargs):
        kwargs['headers'] = kwargs.get('headers', {})
        kwargs['headers']['accept'] = 'application/json'
        super(JsonRequest, self).__init__(*args, **kwargs)
