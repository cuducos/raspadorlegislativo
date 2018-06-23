from decouple import Csv


class Keyword(Csv):

    def __init__(self, *args, **kwargs):
        kwargs['post_process'] = set
        super(Keyword, self).__init__(*args, **kwargs)

    def __call__(self, value):
        return super(Keyword, self).__call__(value.lower())
