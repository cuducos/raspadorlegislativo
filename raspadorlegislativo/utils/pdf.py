from PyPDF2 import PdfFileReader


def extract_text(path):
    with open(path, 'rb') as fobj:
        pdf = PdfFileReader(fobj)
        pages = (pdf.getPage(num).extractText() for num in range(pdf.numPages))
        contents = '\n'.join(pages)

    return contents
