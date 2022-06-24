# Knovleks

Personal Search Engine for different types of resources.

![Screenshot of Knovleks TUI](https://user-images.githubusercontent.com/4940804/175700234-41b43332-7031-4852-a397-d6af8a8577d2.png)

Knovleks can currently index websites, pdf files and text notes.

- [Install](#install)
- [Usage](#usage)
  * [Index](#index)
  * [Search](#search)
  * [Tag filter](#tag-filter)
  * [TUI](#tui)
    + [Searchbar focused](#searchbar-focused)
    + [Results focused](#results-focused)

## Install

```
pip install knovleks
```

## Usage

```
Usage: knovleks [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  index
  search      full-text search
  tag-filter  tag filter
  tui         terminal user interface (experimental)
```

### Index

```
Usage: knovleks index [OPTIONS] DOCUMENT

Options:
  -t, --tag TEXT
  --title TEXT
  -d, --type, --document-type TEXT
  -h, --help                      Show this message and exit.
```

### Search

```
Usage: knovleks search [OPTIONS] QUERY

  full-text search

Options:
  -t, --tag TEXT
  -st, --show-tags
  -l, --limit INTEGER
  -dt, --doc-type TEXT
  -ft, --full-text      display full text
  -h, --help            Show this message and exit.
```

### Tag filter

```
Usage: knovleks tag-filter [OPTIONS] [TAG]...

  tag filter

Options:
  -st, --show-tags
  -l, --limit INTEGER
  -dt, --doc-type TEXT
  -h, --help            Show this message and exit.
```

### TUI

```
Switch focus: TAB
Next result: ctrl+j
Previous result: ctrl+k
Open result without closing: ctrl+l
```

#### Searchbar focused

```
Exit: ESC
```

#### Results focused

```
Switch focus to searchbar: ESC
Open result: Enter
```
