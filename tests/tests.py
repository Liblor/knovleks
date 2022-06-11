import unittest
from collections import defaultdict

from context import Knovleks, SearchSnipOptions, IdocumentType, DocPart


THE_LOVELY_LADY = """The walls of the Wonderful House rose up straight and
shining, pale greenish gold as the slant sunlight on the orchard grass under
the apple trees; the windows that sprang arching to the summer blueness let in
the scent of the cluster rose at the turn of the fence, beginning to rise above
the dusty smell of the country roads, and the evening clamour of the birds in
Bloombury wood. As it dimmed and withdrew, the shining of the walls came out
more clearly. Peter saw then that they were all of coloured pictures wrought
flat upon the gold, and as the glow of it increased they began to swell and
stir like a wood waking. They leaned out from the walls, looking all one way
toward the increasing light and tap-tap of the Princess’ feet along the
halls."""


class DocumentTypeMock(IdocumentType):
    def parse(self):
        pass

    def open_doc(self):
        pass


class TestKnovleks(unittest.TestCase):
    # TODO: add tests for metadata
    def setUp(self):
        self.docs = [
            DocumentTypeMock(
                doc_type="note",
                href="/tmp/lady.txt",
                title="The Lovely Lady",
                tags={"roman", "excerpt"},
                metadata={"author": "Austin, Mary",
                          "license": "public domain"},
                parts=[DocPart(THE_LOVELY_LADY)]),
            DocumentTypeMock(
                doc_type="note",
                href="/tmp/test.txt",
                title="note",
                tags={"random", "excerpt"},
                parts=[DocPart(("The sun shines particularly "
                                "strongly when it's noon."), 1),
                       DocPart(("This is another note. The man "
                                "was swimming in the lake."), 2)]),
            DocumentTypeMock(
                doc_type="pdf",
                href="/tmp/test2.pdf",
                title="Random Pdf",
                tags={"document"},
                metadata={"author": "Barbara Estard"},
                parts=[DocPart("This is some random text.", 1),
                       DocPart("The weather is great for swimming.", 2)])
        ]
        self.k = Knovleks(defaultdict(DocumentTypeMock), ":memory:")

    def get_id_tags(self):
        cur = self.k.db_con.cursor()
        cur.execute("SELECT id, tag FROM tags;")
        res = cur.fetchall()
        if len(res) > 0:
            fetched_ids, fetched_tags = zip(*res)
        else:
            fetched_ids, fetched_tags = (tuple(), tuple())
        cur.close()
        return frozenset(fetched_ids), frozenset(fetched_tags)

    def test_add_tags_3_elems(self):
        """
        Test that tags are being added to the database
        """
        in_tags = {'tag1', 'tag2', 'tag3'}

        returned_ids = self.k.add_tags(in_tags)

        fetched_ids, fetched_tags = self.get_id_tags()

        self.assertEqual(len(returned_ids), len(in_tags))
        self.assertEqual(returned_ids, set(fetched_ids))
        self.assertEqual(set(fetched_tags), in_tags)

    def test_add_tags_0_elems(self):
        """
        Test that add_tags works with empty set.
        """
        in_tags = set()

        returned_ids = self.k.add_tags(in_tags)

        self.assertEqual(len(returned_ids), len(in_tags))
        self.assertEqual(returned_ids, set())

    def test_add_tags_multiple_calls(self):
        """
        Test that add_tags works with with overlaps
        """
        in_tags1 = {'tag1', 'tag2', 'tag3', 'tag4'}
        in_tags2 = {'tag3', 'tag4', 'tag5', 'tag6', 'tag7'}
        all_tags = in_tags1 | in_tags2

        returned_ids1 = self.k.add_tags(in_tags1)
        returned_ids2 = self.k.add_tags(in_tags2)

        fetched_ids, fetched_tags = self.get_id_tags()

        self.assertEqual(len(returned_ids1), len(in_tags1))
        self.assertEqual(len(returned_ids2), len(in_tags2))
        self.assertEqual(len(returned_ids1 & returned_ids2),
                         len(in_tags1 & in_tags2))
        self.assertEqual(set(fetched_tags), all_tags)

    def test__upsert_doc_1_elem(self):
        """
        Test that _upsert_doc which is used by index_document works with one
        document.
        """
        self.k._upsert_doc(self.docs[0])

        cur = self.k.db_con.cursor()
        cur.execute("SELECT href FROM documents;")
        el = cur.fetchone()
        self.assertEqual(el[0], self.docs[0].href)

    def test__upsert_doc_3_elem(self):
        """
        Test that _upsert_doc which is used by index_document works with one
        document.
        """
        for d in self.docs:
            self.k._upsert_doc(d)

        cur = self.k.db_con.cursor()
        cur.execute("SELECT href FROM documents;")
        elems = set([el[0] for el in cur.fetchall()])
        self.assertEqual(len(elems), len(self.docs))
        self.assertEqual(elems, set(map(lambda x: x.href, self.docs)))

        tag = "excerpt"
        cur.execute(("SELECT href FROM tags "
                     "JOIN doc_tag dt ON dt.tag_id=tags.id "
                     "JOIN documents d ON d.id = dt.doc_id "
                     "WHERE tags.tag = ?;"), (tag,))
        elems = set([el[0] for el in cur.fetchall()])
        excerpt_docs = set([d.href for d in self.docs if tag in d.tags])
        self.assertEqual(set(elems), excerpt_docs)

    def test__upsert_doc_3_elem_update_tag(self):
        """
        Test that _upsert_doc when document tags are updated.
        """
        for d in self.docs:
            self.k._upsert_doc(d)
        self.docs[1].tags = {"random", "random2"}
        self.test__upsert_doc_3_elem()
        self.docs[1].tags = {"random", "random2", "excerpt"}
        self.docs[2].tags.add("excerpt")
        self.test__upsert_doc_3_elem()

    def test__upsert_doc_3_elem_update_parts(self):
        """
        Test that _upsert_doc when document parts are updated.
        """
        for d in self.docs:
            self.k._upsert_doc(d)
        # change
        self.docs[0].parts = [DocPart("hello world")]
        # delete and change
        self.docs[1].parts = [DocPart(THE_LOVELY_LADY)]
        # add
        self.docs[2].parts.append(
            DocPart("This lovely text is added here.", 3))
        self.test__upsert_doc_3_elem()
        cur = self.k.db_con.cursor()
        cur.execute("SELECT id FROM doc_parts;")

        num_parts = sum([len(el.parts) for el in self.docs])
        self.assertEqual(len(cur.fetchall()), num_parts)

    def test_search(self):
        self.test__upsert_doc_3_elem()
        self.assertEqual(len(list(self.k.search("shine"))), 2)
        self.assertEqual(len(list(self.k.search("shine", limit=1))), 1)
        self.assertEqual(len(list(self.k.search("swim", ))), 2)
        self.assertEqual(len(list(self.k.search("swim", doc_type='pdf'))), 1)

    def test_search_snip(self):
        self.test__upsert_doc_3_elem()
        so = SearchSnipOptions("<b>", "</b>")
        result = list(self.k.search("shine", snip=so))
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0][3].find("<b>") >= 0)

    def test_search_tags(self):
        self.test__upsert_doc_3_elem()
        self.assertEqual(len(list(self.k.search("shine", tags={"roman"}))), 1)
        self.assertEqual(
            len(list(self.k.search("shine", tags={"excerpt"}))), 2)
        self.assertEqual(
            len(list(self.k.search("shine", tags={"roman", "excerpt"}))), 1)
        self.assertEqual(len(list(self.k.search("swim", tags={"non"}))), 0)

    def test_href_exists(self):
        self.assertFalse(self.k.href_exists(self.docs[0].href))
        self.test__upsert_doc_3_elem()
        self.assertTrue(self.k.href_exists(self.docs[0].href))
        self.assertFalse(self.k.href_exists("nono"))

    def test_filter_by_tags(self):
        self.test__upsert_doc_3_elem()
        r = len(list(self.k.filter_by_tags({"roman", "excerpt"})))
        self.assertEqual(r, 1)
        r = len(list(self.k.filter_by_tags({"excerpt", "no"})))
        self.assertEqual(r, 0)
        r = len(list(self.k.filter_by_tags({"excerpt"})))
        self.assertEqual(r, 2)


if __name__ == '__main__':
    unittest.main()
