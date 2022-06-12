#!/usr/bin/env python3

from ..idocument_type import IdocumentType, DocPart
from newspaper import Article

import webbrowser


class WebsiteDocument(IdocumentType):
    def parse(self):
        self.doc_type = "website"
        article = Article(self.href)
        article.download()
        article.parse()
        self.title = article.title
        self.tags |= frozenset(article.keywords)
        self.metadata = {"author": article.authors}
        self.parts.append(DocPart(doccontent=article.text))

    @staticmethod
    def open_doc(href, elem_idx):
        webbrowser.open(href)
