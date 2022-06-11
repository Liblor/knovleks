#!/usr/bin/env python3

from ..idocument_type import IdocumentType, DocPart


class NoteDocument(IdocumentType):
    def parse(self):
        self.doc_type = "note"
        with open(self.href, 'r') as f:
            content = f.read()
        self.parts.append(DocPart(doccontent=content))
