#!/usr/bin/env python3

import subprocess
import fitz as pdfreader
from ..idocument_type import IdocumentType, DocPart


class PdfDocument(IdocumentType):
    def parse(self):
        self.doc_type = "pdf"
        with pdfreader.open(self.href) as doc:
            for i, page in enumerate(doc, 1):
                text = page.get_text()
                self.parts.append(DocPart(doccontent=text, elem_idx=i))

    @staticmethod
    def open_doc(href, elem_idx):
        dn = subprocess.DEVNULL
        subprocess.Popen(["/usr/bin/zathura", f"{href}", "-P", f"{elem_idx}"],
                         stdin=dn, stdout=dn, stderr=dn, close_fds=True)
