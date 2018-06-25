from datetime import datetime


def feed(name):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    return f'data/{timestamp}-{name}.csv'
