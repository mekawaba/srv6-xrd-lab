#!/usr/bin/env python3
"""Convert the Word lab guides into MkDocs Markdown pages.

Usage:
    python tools/docx2md.py <directory containing Lab_guide_*.docx>

CLI output / configuration in the guides lives in floating text boxes, which
generic converters flatten into plain paragraphs. This script walks the
document in order and turns every text box into a <pre><code> block while
keeping bold and highlighted (marker) text.
"""

import html
import re
import shutil
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn

MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
A_BLIP = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"

EMU_PER_INCH = 914400
PAGE_TEXT_WIDTH_IN = 6.5

CHAPTERS = {
    "01": ("01-sr-mpls-basic", "SR-MPLS 基本設定"),
    "02": ("02-l3vpn", "L3VPN"),
    "03": ("03-srte-explicit", "SR-TE Explicit Path"),
    "04": ("04-srte-dynamic", "SR-TE Dynamic Path"),
    "05": ("05-evpn-vpws", "EVPN VPWS"),
    "06": ("06-evpn-vpls", "EVPN VPLS"),
}

PASSWORD_RE = re.compile(
    r"((?:Password|パスワード)\s*[:：]\s*(?:</?[a-z]+[^>]*>)*)[^\s<）)、。]+", re.I)
PASSWORD_MASK = "講師よりお伝えします"
URL_RE = re.compile(r"https?://[^\s<>）)]+")

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


def redact(text):
    return PASSWORD_RE.sub(lambda m: m.group(1) + PASSWORD_MASK, text)


# ---------------------------------------------------------------- run helpers

def iter_runs(container):
    """Yield w:r elements of a paragraph in order, descending into wrappers."""
    for child in container:
        tag = child.tag
        if tag == qn("w:r"):
            yield child
        elif tag in (qn("w:hyperlink"), qn("w:ins"), qn("w:smartTag"),
                     qn("w:customXml"), qn("w:fldSimple")):
            yield from iter_runs(child)
        elif tag == qn("w:sdt"):
            content = child.find(qn("w:sdtContent"))
            if content is not None:
                yield from iter_runs(content)


def run_format(r):
    rpr = r.find(qn("w:rPr"))
    bold = mark = False
    color = None
    if rpr is not None:
        b = rpr.find(qn("w:b"))
        bold = b is not None and b.get(qn("w:val")) not in ("0", "false")
        hl = rpr.find(qn("w:highlight"))
        mark = hl is not None and hl.get(qn("w:val")) != "none"
        shd = rpr.find(qn("w:shd"))
        if shd is not None and shd.get(qn("w:fill")) not in (None, "auto", "FFFFFF"):
            mark = True
        c = rpr.find(qn("w:color"))
        if c is not None and c.get(qn("w:val")) not in (None, "auto", "000000"):
            color = c.get(qn("w:val"))
    return bold, mark, color


def run_text(r, tab="    "):
    out = []
    for el in r:
        if el.tag == qn("w:t"):
            out.append(el.text or "")
        elif el.tag == qn("w:tab"):
            out.append(tab)
        elif el.tag in (qn("w:br"), qn("w:cr")):
            out.append("\n")
        elif el.tag == qn("w:noBreakHyphen"):
            out.append("-")
    return "".join(out)


def styled_segments(runs, tab="    "):
    """Merge adjacent runs with identical formatting -> [(text, fmt)]."""
    segs = []
    for r in runs:
        t = run_text(r, tab)
        if not t:
            continue
        fmt = run_format(r)
        if segs and segs[-1][1] == fmt:
            segs[-1] = (segs[-1][0] + t, fmt)
        else:
            segs.append((t, fmt))
    return segs


def wrap(text, fmt):
    bold, mark, color = fmt
    if color:
        text = f'<span style="color:#{color}">{text}</span>'
    if mark:
        text = f"<mark>{text}</mark>"
    if bold:
        text = f"<strong>{text}</strong>"
    return text


def split_ws(s):
    """Keep surrounding whitespace outside of inline tags."""
    m = re.match(r"^(\s*)(.*?)(\s*)$", s, re.S)
    return m.group(1), m.group(2), m.group(3)


# ------------------------------------------------------------- markdown text

MD_SPECIAL = re.compile(r"([\\`*_\[\]])")


def md_escape(text):
    parts = []
    last = 0
    for m in URL_RE.finditer(text):
        parts.append(MD_SPECIAL.sub(r"\\\1", html.escape(text[last:m.start()], quote=False)))
        parts.append(f"<{m.group(0)}>")
        last = m.end()
    parts.append(MD_SPECIAL.sub(r"\\\1", html.escape(text[last:], quote=False)))
    return "".join(parts)


CJK_RE = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")


def command_text(runs):
    """Return the text if the paragraph is a bold, non-Japanese command line."""
    segs = styled_segments(runs, tab=" ")
    text = "".join(t for t, _ in segs).strip()
    if not text or CJK_RE.search(text):
        return None
    if all(fmt[0] for t, fmt in segs if t.strip()):
        return redact(text)
    return None


def inline_markdown(runs):
    out = []
    for text, fmt in styled_segments(runs, tab=" "):
        lead, core, trail = split_ws(text)
        if any(fmt) and core:
            out.append(lead + wrap(md_escape(core), fmt) + trail)
        else:
            out.append(md_escape(text))
    s = redact("".join(out).strip())
    s = s.replace("\n", "<br>\n")
    s = re.sub(r"^(\d+)\.", r"\1\\.", s)
    s = re.sub(r"^([-+#>])", r"\\\1", s)
    return s


# ----------------------------------------------------------------- code boxes

def code_block(txbx):
    lines = []
    for p in txbx.iter(qn("w:p")):
        line = []
        for text, fmt in styled_segments(iter_runs(p)):
            text = html.escape(text, quote=False)
            line.append(wrap(text, fmt) if any(fmt) and text.strip() else text)
        lines.append(redact("".join(line)))
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return None
    body = "\n".join(lines).replace("\u3000", " ")
    return f'<pre class="cli"><code>{body}</code></pre>'


# --------------------------------------------------------------------- images

class ImageWriter:
    def __init__(self, document, out_dir):
        self.document = document
        self.out_dir = out_dir
        self.count = 0

    def write(self, drawing):
        blip = drawing.find(".//" + A_BLIP)
        if blip is None:
            return None
        rid = blip.get(R_EMBED)
        part = self.document.part.related_parts.get(rid)
        if part is None:
            return None
        self.count += 1
        ext = Path(str(part.partname)).suffix.lower()
        name = f"image{self.count:02d}{ext}"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / name).write_bytes(part.blob)

        extent = drawing.find(".//" + WP + "extent")
        attr = ""
        if extent is not None:
            width_in = int(extent.get("cx")) / EMU_PER_INCH
            pct = min(100, round(width_in / PAGE_TEXT_WIDTH_IN * 100))
            attr = f'{{ style="width:{pct}%" }}'
        return f"![](images/{name}){attr}"


# ------------------------------------------------------------------ paragraph

def drawings_in_run(r):
    """Return drawing elements of a run, choosing mc:Choice over mc:Fallback."""
    found = []
    for el in r:
        if el.tag == MC + "AlternateContent":
            choice = el.find(MC + "Choice")
            if choice is not None:
                found.extend(choice.iter(qn("w:drawing")))
        elif el.tag == qn("w:drawing"):
            found.append(el)
    return found


def list_kind(document, p):
    numpr = p.find(qn("w:pPr") + "/" + qn("w:numPr"))
    if numpr is None:
        return None
    num_id = numpr.find(qn("w:numId")).get(qn("w:val"))
    ilvl_el = numpr.find(qn("w:ilvl"))
    ilvl = ilvl_el.get(qn("w:val")) if ilvl_el is not None else "0"
    numbering = document.part.numbering_part.element
    num = numbering.find(f"{qn('w:num')}[@{qn('w:numId')}='{num_id}']")
    if num is None:
        return "bullet"
    abs_id = num.find(qn("w:abstractNumId")).get(qn("w:val"))
    abstract = numbering.find(f"{qn('w:abstractNum')}[@{qn('w:abstractNumId')}='{abs_id}']")
    lvl = abstract.find(f"{qn('w:lvl')}[@{qn('w:ilvl')}='{ilvl}']")
    fmt = lvl.find(qn("w:numFmt")).get(qn("w:val")) if lvl is not None else "bullet"
    return "bullet" if fmt == "bullet" else "ordered"


def render(blocks):
    md = []
    for i, (kind, content) in enumerate(blocks):
        if kind == "command":
            content = f"```text\n{content}\n```"
        if i:
            md.append("\n" if kind == "list" and blocks[i - 1][0] == "list" else "\n\n")
        md.append(content)
    return "".join(md) + "\n"


def convert(docx_path, number, slug, title):
    """Write docs/<slug>/index.md and return the blocks of unnumbered sections.

    Unnumbered Heading 1 sections (e.g. "ラボについて") are common lab
    information and are moved to the top page instead of the chapter page.
    """
    document = docx.Document(str(docx_path))
    out_dir = DOCS_DIR / slug
    if out_dir.exists():
        shutil.rmtree(out_dir)
    images = ImageWriter(document, out_dir / "images")

    chapter = [("title", f"# {number}. {title}")]
    intro = []
    blocks = chapter
    started = False
    heading_no = 0

    for p in document.element.body.iter(qn("w:p")):
        if p.getparent().tag != qn("w:body"):
            continue
        style_id = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
        style_id = style_id.get(qn("w:val")) if style_id is not None else ""
        style = document.styles.get_by_id(style_id, docx.enum.style.WD_STYLE_TYPE.PARAGRAPH)
        style_name = style.name if style is not None else "Normal"
        is_heading = style_name.startswith("Heading")

        if is_heading:
            started = True
        if not started:
            continue

        text_runs, extras = [], []
        for r in iter_runs(p):
            for d in drawings_in_run(r):
                txbx = d.find(".//" + qn("w:txbxContent"))
                if txbx is not None:
                    block = code_block(txbx)
                    if block:
                        extras.append(("code", block))
                else:
                    img = images.write(d)
                    if img:
                        extras.append(("image", img))
            text_runs.append(r)

        text = inline_markdown(text_runs)
        text_plain = "".join(run_text(r) for r in text_runs).replace("\u3000", "").strip()
        command = None if is_heading else command_text(text_runs)

        if command:
            if blocks and blocks[-1][0] == "command":
                blocks[-1] = ("command", blocks[-1][1] + "\n" + command)
            else:
                blocks.append(("command", command))
        elif text_plain:
            if is_heading:
                level = int(re.sub(r"\D", "", style_name) or 1) + 1
                numbered = p.find(qn("w:pPr") + "/" + qn("w:numPr")) is not None
                manual = re.match(r"^\d+\\?\.\d+\s*", text)
                if manual:
                    text = text[manual.end():]
                if level == 2:
                    if numbered or manual:
                        heading_no += 1
                        text = f"{int(number)}.{heading_no} {text.strip()}"
                        blocks = chapter
                    else:
                        blocks = intro
                blocks.append(("heading", "#" * level + " " + text))
            elif (kind := list_kind(document, p)) is not None:
                marker = "-" if kind == "bullet" else "1."
                blocks.append(("list", f"{marker} {text}"))
            elif re.match(r"^[•・]", text_plain):
                blocks.append(("list", "- " + re.sub(r"^[•・]\s*", "", text)))
            elif re.match(r"^ゴール\s*[:：]", text_plain):
                goal = re.sub(r"^ゴール\s*[:：]\s*", "", text)
                blocks.append(("para", f'!!! abstract "ゴール"\n\n    {goal}'))
            else:
                blocks.append(("para", text.lstrip("\u3000 ")))
        blocks.extend(extras)

    (out_dir / "index.md").write_text(render(chapter), encoding="utf-8")
    print(f"{docx_path.name} -> docs/{slug}/index.md ({images.count} images)")
    return [(kind, content.replace("](images/", f"]({slug}/images/"))
            for kind, content in intro]


def write_top_page(intro, chapters):
    rows = "\n".join(f"| {no} | [{title}]({slug}/index.md) |" for no, slug, title in chapters)
    first = chapters[0]
    blocks = [
        ("title", "# Segment Routing ハンズオン"),
        ("para", "このハンズオンでは、CML 上の Cisco 8000 (IOS XR) ルータを使って "
                 "SR-MPLS の基本設定から L3VPN、SR-TE、EVPN までを順に体験します。"),
        ("heading", "## ラボ一覧"),
        ("para", "| No. | ラボ |\n|:---:|:---|\n" + rows),
        *intro,
        ("heading", "## 次のステップ"),
        ("para", f"環境にアクセスできたら [{first[0]}. {first[2]}]({first[1]}/index.md) に進んでください。"),
    ]
    (DOCS_DIR / "index.md").write_text(render(blocks), encoding="utf-8")
    print("-> docs/index.md")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    intro, done = [], []
    for path in sorted(src.glob("Lab_guide_*.docx")):
        m = re.match(r"Lab_guide_(\d+)", path.name)
        if not m or m.group(1) not in CHAPTERS:
            print(f"skip: {path.name}")
            continue
        slug, title = CHAPTERS[m.group(1)]
        intro += convert(path, m.group(1), slug, title)
        done.append((m.group(1), slug, title))
    write_top_page(intro, done)


if __name__ == "__main__":
    main()
