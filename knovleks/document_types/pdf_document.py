#!/usr/bin/env python3

import fitz as pdfreader
from ..idocument_type import IdocumentType, DocPart


class PdfDocument(IdocumentType):
    def parse(self):
        self.doc_type = "pdf"
        with pdfreader.open(self.href) as doc:
            for i, page in enumerate(doc, 1):
                text = page.get_text()
                self.parts.append(DocPart(doccontent=text, elem_idx=i))
