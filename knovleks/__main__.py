#!/usr/bin/env python3

import textwrap
import shutil
import click

from typing import Mapping, Type, Tuple, Optional
from .knovleks import Knovleks, SearchSnipOptions
from .document_types import NoteDocument, PdfDocument, WebsiteDocument
from .idocument_type import IdocumentType
from .tui import KnovTui


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


def is_url(path: str) -> bool:
    url_prefixes = ["https://", "http://"]
    path = path.lower()
    return any(map(path.startswith, url_prefixes))


def determine_doc_type(document: str) -> str:
    # TODO: determine ooc based on configuration file
    if is_url(document):
        return "website"
    # XXX: filetype shouldn't be determined based on extension
    elif document.endswith(".pdf"):
        return "pdf"
    else:
        return "note"


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.pass_context
def cli(ctx):
    supported_types = get_supported_document_types()
    ctx.obj = Knovleks(supported_types)


@click.command(help="")
@click.argument("document")
@click.option("-t", "--tag", multiple=True)
@click.option("--title", default="")
@click.option("-d", "--type", "--document-type", default="auto")
@click.pass_obj
def index(knov: Knovleks, document: str, tag: Tuple[str],
          title: str, type: str):
    if type == "auto":
        type = determine_doc_type(document)
    knov.index_document(type, document, title, set(tag))


@click.command(help="full-text search")
@click.argument("query")
@click.option("-t", "--tag", multiple=True)
@click.option("-st", "--show-tags", is_flag=True, default=False)
@click.option("-l", "--limit", type=int)
@click.option("-dt", "--doc-type")
@click.option("-ft", "--full-text", is_flag=True, default=False,
              help="display full text")
@click.pass_obj
def search(knov: Knovleks, query: str, tag: Tuple[str], show_tags: bool,
           limit: Optional[int], doc_type: Optional[str], full_text: bool):
    so = None if full_text else SearchSnipOptions(bcolors.OKBLUE, bcolors.ENDC)
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


@click.command(help="tag filter")
@click.argument("tag", nargs=-1)
@click.option("-st", "--show-tags", is_flag=True, default=False)
@click.option("-l", "--limit", type=int)
@click.option("-dt", "--doc-type")
@click.pass_obj
def tag_filter(knov: Knovleks, tag: Tuple[str], show_tags: bool,
               limit: Optional[int], doc_type: Optional[str]):
    sq = knov.filter_by_tags(set(tag), limit=limit, doc_type=doc_type)
    for result in sq:
        href = result[0]
        print(f"{bcolors.OKGREEN}{href}{bcolors.ENDC}")
        if show_tags:
            returned_tags = ', '.join(knov.get_tags_by_href(href))
            print(f"tags: {bcolors.OKCYAN}{returned_tags}{bcolors.ENDC}")
        print()


@click.command(help="terminal user interface (experimental)")
@click.pass_obj
def tui(knov: Knovleks):
    KnovTui.run(knovleks=knov, title=f"{__name__}")


cli.add_command(index)
cli.add_command(search)
cli.add_command(tag_filter)
cli.add_command(tui)

if __name__ == '__main__':
    cli()
