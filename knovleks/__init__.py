#!/usr/bin/env python
import sqlite3
from pathlib import Path
from typing import Set, Optional, Sequence

from knovleks.idocument_type import IdocumentType


__name__ = "knovleks"
__version__ = "0.0.1alpha"


DB_SCHEME = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    type TEXT,
    href TEXT,
    title TEXT
);


CREATE TABLE IF NOT EXISTS doc_parts (
    id INTEGER PRIMARY KEY,
    doc_id INTEGER,
    elem_idx INTEGER,
    doccontent TEXT,
    FOREIGN KEY(doc_id) REFERENCES documents(id)
);
CREATE VIRTUAL TABLE IF NOT EXISTS doc_parts_fts USING fts5(
    doccontent,
    content=doc_parts,
    content_rowid=id,
    tokenize = 'porter unicode61'
);
-- Triggers to keep the FTS index up to date.
CREATE TRIGGER IF NOT EXISTS doc_parts_ai AFTER INSERT ON doc_parts BEGIN
  INSERT INTO doc_parts_fts(rowid, doccontent) VALUES (new.id, new.doccontent);
END;
CREATE TRIGGER IF NOT EXISTS doc_parts_ad AFTER DELETE ON doc_parts BEGIN
  INSERT INTO doc_parts_fts(doc_parts_fts, rowid, doccontent)
         VALUES('delete', old.id, old.doccontent);
END;
CREATE TRIGGER IF NOT EXISTS doc_parts_au AFTER UPDATE ON doc_parts BEGIN
  INSERT INTO doc_parts_fts(doc_parts_fts, rowid, doccontent)
         VALUES('delete', old.id, old.doccontent);
  INSERT INTO doc_parts_fts(rowid, doccontent) VALUES (new.id, new.doccontent);
END;


CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    tag TEXT
);


CREATE TABLE IF NOT EXISTS doc_tag (
    id INTEGER PRIMARY KEY,
    doc_id INTEGER,
    tag_id INTEGER,
    FOREIGN KEY(doc_id) REFERENCES documents(id),
    FOREIGN KEY(tag_id) REFERENCES tags(id)
);
"""


class Knovleks:
    def __init__(self,
                 supported_types,
                 db: str = f"~/.config/{__name__}/index.db"):
        if db == ":memory:":
            self.db_con = sqlite3.connect(db)
        else:
            p = Path(db).expanduser().resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            self.db_con = sqlite3.connect(p)
        # self.db_con.row_factory = sqlite3.Row
        self.supported_types = supported_types
        self.db_con.executescript(DB_SCHEME)
        self.db_con.commit()

    def _insert_doc(self, doc: IdocumentType) -> int:
        cur = self.db_con.cursor()
        cur.execute("INSERT INTO documents(type, href, title) VALUES(?,?,?);",
                    (doc.doc_type, doc.href, doc.title))
        id = cur.lastrowid
        insert_q = ("INSERT INTO doc_parts(doc_id, elem_idx, doccontent) "
                    "VALUES(?,?,?);")
        for part in doc.parts:
            cur.execute(insert_q, (id, part.elem_idx, part.doccontent))
        cur.close()
        return id

    def _update_doc(self, doc: IdocumentType, doc_id: int):
        cur = self.db_con.cursor()
        cur.execute("UPDATE documents SET type=?, href=?, title=? WHERE id=?;",
                    (doc.doc_type, doc.href, doc.title, doc_id))
        cur.execute("SELECT id FROM doc_parts WHERE doc_id = ?;", (doc_id,))
        existing_part_ids = [el[0] for el in cur.fetchall()]
        parts = list(doc.parts)
        for part_id, part in zip(existing_part_ids, parts):
            cur.execute(
                "UPDATE doc_parts SET elem_idx=?, doccontent=? WHERE id=?;",
                (part.elem_idx, part.doccontent, part_id))
        for part in parts[len(existing_part_ids):]:
            cur.execute(("INSERT INTO doc_parts(doc_id, elem_idx, doccontent) "
                         "VALUES(?,?,?);"),
                        (doc_id, part.elem_idx, part.doccontent))
        for part_id in existing_part_ids[len(parts):]:
            cur.execute("DELETE FROM doc_parts WHERE id=?;",
                        (part_id,))
        cur.close()

    def _upsert_doc(self, doc: IdocumentType):
        cur = self.db_con.cursor()
        cur.execute("SELECT id FROM documents WHERE href=?;", (doc.href,))
        el = cur.fetchone()
        if el is None:
            id = self._insert_doc(doc)
        else:
            id = el[0]
            self._update_doc(doc, id)
        tag_ids = self.add_tags(doc.tags)
        self._update_doc_tag_link(id, tag_ids)
        self.db_con.commit()

    def _insert_tag(self, tag: str) -> int:
        """
        Insert a tag to the tags database, but does not write/commit the DB.
        """
        cur = self.db_con.cursor()
        cur.execute("INSERT INTO tags(tag) VALUES (?)", (tag,))
        id = cur.lastrowid
        cur.close()
        return id

    def _update_doc_tag_link(self, doc_id: int, tag_ids: Set[int]):
        cur = self.db_con.cursor()
        cur.execute("SELECT tag_id FROM doc_tag WHERE doc_id=?;", (doc_id,))
        existing_tag_ids = frozenset([el[0] for el in cur.fetchall()])
        tag_ids_to_remove = existing_tag_ids - tag_ids
        new_tag_ids = tag_ids - existing_tag_ids
        for tag_id in tag_ids_to_remove:
            cur.execute("DELETE FROM doc_tag WHERE doc_id=? AND tag_id=?;",
                        (doc_id, tag_id))
        for tag_id in new_tag_ids:
            cur.execute("INSERT INTO doc_tag(doc_id, tag_id) VALUES (?,?);",
                        (doc_id, tag_id))
        self.db_con.commit()
        cur.close()

    def add_tags(self, tags: Set[str]) -> Set[int]:
        if len(tags) <= 0: return set([])
        cur = self.db_con.cursor()
        qm = ','.join("?" * len(tags))
        q = f"SELECT id, tag FROM tags WHERE tag in ({qm});"
        cur.execute(q, tuple(tags))
        res = cur.fetchall()
        exi_ids, existing_tags = zip(*res) if len(res) > 0 else (set(), set())
        mis_tags = tags - frozenset(existing_tags)
        ids_set = set(exi_ids)
        for t in mis_tags:
            id = self._insert_tag(t)
            ids_set.add(id)
        self.db_con.commit()
        cur.close()
        return ids_set

    def index_document(self, doc_type: str, href: str, title: str,
                       tags: Set[str]):
        doc = self.supported_types[doc_type](href, title, tags=tags)
        self._upsert_doc(doc)

    def _join_tag_query(self, tags: Sequence[str]):
        if not tags: return ""
        qm = ','.join("?" * len(tags))
        q = (f"JOIN tags t ON t.tag in ({qm}) "
             "JOIN doc_tag dt ON t.id = dt.tag_id AND dt.doc_id = d.id ")
        return q

    def search(self, search_query: str, tags: Sequence[str] = (),
               limit: Optional[int] = None):
        parameters = []
        query = ("SELECT DISTINCT href, elem_idx, title, dpf.doccontent "
                 "FROM doc_parts dp, doc_parts_fts dpf, documents d "
                 f"{self._join_tag_query(tags)}"
                 "WHERE dpf.rowid = dp.id AND dp.doc_id = d.id AND "
                 "dpf.doccontent MATCH ? ORDER BY rank")
        parameters.extend(tags)
        parameters.append(search_query)
        if limit is not None:
            parameters.append(f"{limit}")
            query += " LIMIT ?"
        yield from self.db_con.execute(query, parameters)
