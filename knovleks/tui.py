#!/usr/bin/env python3

# XXX: Hacky first attempt with textual

from collections.abc import Collection
from typing import Set, Tuple

from rich.align import Align
from rich import box
from rich.console import RenderableType
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
import rich.repr

from textual import events
from textual.app import App
from textual.widget import Reactive, Widget
from textual.widgets import ScrollView
from textual_inputs import TextInput

from .knovleks import Knovleks, SearchSnipOptions


class SearchEntry(Text):
    def __init__(self, href: str, content: Text, elem_idx: int,
                 doc_type: str, tags: Collection[str] = frozenset()):
        super(SearchEntry, self).__init__()
        self.href = href
        self.elem_idx = elem_idx
        self.doc_type = doc_type
        self.append(f"{href}", style="green")
        if self.elem_idx:
            self.append(f" : page {elem_idx}")
        self.append("\n")
        if tags:
            ts = f'{", ".join(tags)}\n'
            self.append(ts, style="cyan")
        self.append_text(content)


class SearchBar(TextInput):
    def __init__(self, knovleks: Knovleks, result_view=None):
        super(SearchBar, self).__init__()
        self.result_view = result_view
        self.knov = knovleks
        self.rw = ResultWidget()

    async def on_key(self, event: events.Key) -> None:
        await self.dispatch_key(event)

    async def simple_parse(self, query) -> Tuple[str, Set[str]]:
        t = query.split()
        is_tag = lambda x: x.find("tag:") >= 0
        tags = set(map(lambda x: x[4:], filter(is_tag, t))) - {'', ' '}
        search_q = " ".join(filter(lambda x: not is_tag(x), t))
        return search_q, tags

    async def key_enter(self, event: events.Key) -> None:
        if self.value.strip() == "": return
        so = SearchSnipOptions("[bold blue]", "[/bold blue]")
        q, s_tags = await self.simple_parse(self.value)
        if not q and not s_tags: return
        results = []
        if q.strip():
            sq = self.knov.search(q, tags=s_tags, limit=40, snip=so)
            for result in sq:
                href = result[0]
                content = Text.from_markup(result[3])
                page = int(result[1])
                doc_type = result[4]
                tags = set(self.knov.get_tags_by_href(href))
                results.append(SearchEntry(href, content, page, doc_type,
                                           tags))
        else:
            sq = self.knov.filter_by_tags(set(s_tags))
            for result in sq:
                href = result[0]
                doc_type = result[2]
                tags = set(self.knov.get_tags_by_href(href))
                results.append(SearchEntry(href, Text(), 0, doc_type, tags))
        self.rw = ResultWidget(results=results)
        await self.rw.focus()
        await self.result_view.update(self.rw)


@rich.repr.auto(angular=False)
class ResultWidget(Widget, can_focus=True):

    selected: Reactive[int] = Reactive(0)

    def __rich_repr__(self) -> rich.repr.RichReprResult:
        yield Align.center(self.table, vertical="middle")

    def __init__(self, *args, results: Collection[SearchEntry] = tuple(),
                 title: str = "Results", **kwargs):
        self.title = title
        self.table = Table(show_header=False)
        self.table.box = box.SIMPLE
        self.arrow = Text.from_markup("[bold green]>[/bold green]")
        self.results = results
        for result in results:
            self.table.add_row("", result)
        for row in self.table.rows:
            row.style = 'dim'
        if results:
            self.table.rows[self.selected].style = 'bold'
            self.table.columns[0]._cells[self.selected] = self.arrow
            self.results = results
        super().__init__(*args, **kwargs)

    def render(self) -> RenderableType:
        return Panel(self.table, box=box.SQUARE)

    async def move(self, pos):
        if len(self.results) > self.selected + pos >= 0:
            self.table.rows[self.selected].style = 'dim'
            self.table.columns[0]._cells[self.selected] = ""
            self.selected += pos
            self.table.rows[self.selected].style = 'bold'
            self.table.columns[0]._cells[self.selected] = self.arrow

    async def on_key(self, event: events.Key):
        await self.dispatch_key(event)

    async def key_down(self, event: events.Key):
        await self.move(1)

    async def key_up(self, event: events.Key):
        await self.move(-1)

    async def key_j(self, event: events.Key):
        await self.move(1)

    async def key_k(self, event: events.Key):
        await self.move(-1)


class KnovTui(App):
    def __init__(self, knovleks: Knovleks, *args, **kwargs):
        self.knov = knovleks
        super().__init__(*args, **kwargs)

    async def on_load(self) -> None:
        await self.bind("ctrl+j", "down")
        await self.bind("ctrl+k", "up")
        await self.bind("ctrl+l", "open_result")
        await self.bind("ctrl+i", "next_tab_index", show=False)

    async def on_mount(self) -> None:
        rw = ResultWidget()
        sv = ScrollView(rw)
        self.search_bar = SearchBar(knovleks=self.knov, result_view=sv)
        await self.search_bar.focus()
        self.sb_focus = True

        grid = await self.view.dock_grid(edge="left", name="left")
        grid.add_column(fraction=1, name="u")
        grid.add_row(fraction=1, name="top", min_size=3)
        grid.add_row(fraction=20, name="middle")
        grid.add_areas(area1="u,top", area2="u,middle", area3="u,bottom")
        grid.place(area1=self.search_bar, area2=sv)

    async def action_down(self) -> None:
        await self.search_bar.rw.move(1)

    async def action_up(self) -> None:
        await self.search_bar.rw.move(-1)

    async def action_focus_searchbar(self):
        self.sb_focus = True
        await self.search_bar.focus()

    async def action_open_result(self):
        selected = self.search_bar.rw.selected
        se = self.search_bar.rw.results[selected]
        self.knov.open_document(se.doc_type, se.href, se.elem_idx)

    async def action_next_tab_index(self) -> None:
        if self.sb_focus:
            await self.search_bar.rw.focus()
        else:
            await self.search_bar.focus()
        self.sb_focus = not self.sb_focus

    async def on_key(self, event: events.Key):
        if event.key == "enter":
            if self.sb_focus:
                self.sb_focus = False
                await self.search_bar.rw.focus()
            else:
                print(event)
                await self.action_open_result()
                quit()
        elif event.key == "escape":
            if self.sb_focus:
                quit()
            else:
                await self.action_focus_searchbar()
