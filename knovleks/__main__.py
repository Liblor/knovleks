#!/usr/bin/env python3

import textwrap
import shutil
import click

from typing import Mapping, Type, Tuple, Optional
from .knovleks import Knovleks, SearchSnipOptions
from .document_types import NoteDocument, PdfDocument, WebsiteDocument
from .idocument_type import *


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_terminal_columns():
    return shutil.get_terminal_size().columns

def print_autobreak(*args, sep=' '):
    width = get_terminal_columns()
    for line in sep.join(map(str, args)).splitlines(True):
        print(*textwrap.wrap(line, width, initial_indent='    ',
            subsequent_indent='    '), sep="\n")

def get_supported_document_types() -> Mapping[str, Type[IdocumentType]]:
    # TODO: make modular
    return {
        "note": NoteDocument,
        "pdf": PdfDocument,
        "website": WebsiteDocument
    }

@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.pass_context
def cli(ctx):
    supported_types = get_supported_document_types()
    ctx.obj = Knovleks(supported_types)

@click.command(help="")
@click.argument("document")
@click.option("-t", "--tag", multiple=True)
@click.option("--title", default="")
@click.option("-d", "--type", "--document-type", default="note")
@click.pass_obj
def index(knov: Knovleks, document: str, tag: Tuple[str], title: str, type: str):
    knov.index_document(type, document, title, set(tag))

@click.command(help="full-text search")
@click.argument("query")
@click.option("-t", "--tag", multiple=True)
@click.option("-st", "--show-tags", is_flag=True, default=False)
@click.option("-l", "--limit", type=int)
@click.option("-dt", "--doc-type")
@click.pass_obj
def search(knov: Knovleks, query: str, tag: Tuple[str], show_tags: bool,
           limit: Optional[int], doc_type: Optional[str]):
    so = SearchSnipOptions(bcolors.OKBLUE, bcolors.ENDC)
    sq = knov.search(query, set(tag), limit=limit, doc_type=doc_type, snip=so)
    for result in sq:
        href = result[0]
        page = int(result[1])
        pstr = f" : page {page}" if page > 0 else ""
        print(f"{bcolors.OKGREEN}{href}{bcolors.ENDC}{pstr}")
        if show_tags:
            returned_tags = ', '.join(knov.get_tags_by_href(href))
            print(f"tags: {bcolors.OKCYAN}{returned_tags}{bcolors.ENDC}")
        print_autobreak(result[3])
        print()


cli.add_command(index)
cli.add_command(search)

if __name__ == '__main__':
    cli()