"""A slide deck, written with the standard library.

A `.pptx` is a zip of XML parts, and a deck of pictures with a title and a
line of text on each needs very few of them: the presentation, one blank
master and layout, a theme, the slides, their pictures, and the content
types that name them all. `pptxgenjs` did this for the review pack from
Node; this does it from Python with nothing installed, so `terrane pack` runs
where `terrane render` runs. Text is a box of paragraphs of runs, each run
with a size, a weight and a color; a picture is a PNG placed in a box. The
zip is written with one fixed timestamp, so the same slides are the same
bytes.

Sizes on the slide are inches, as the Node pack gave them; the file holds
them in EMUs, 914,400 to the inch. Text sizes are points.
"""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union
from xml.sax.saxutils import escape

EMU = 914400
#: PowerPoint's widescreen, pptxgenjs's `LAYOUT_WIDE`: 13 1/3 by 7.5 inches,
#: which is 12,192,000 by 6,858,000 EMUs exactly.
WIDE = (12192000 / EMU, 7.5)
NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
EMPTY_TREE = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
              '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
              '<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
STAMP = (1980, 1, 1, 0, 0, 0)

Run = Tuple[str, dict]
Paragraph = Sequence[Run]


def _emu(inches: float) -> int:
    return int(round(inches * EMU))


def png_size(data: bytes) -> Tuple[int, int]:
    """A PNG's width and height, from the IHDR chunk at the fixed offsets."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def fitted(size: Tuple[int, int], box: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """The place an image of `size` gets in `box`, kept in aspect and
    centered: what the Node pack's `fitted` did."""
    x, y, w, h = box
    scale = min(w / max(size[0], 1), h / max(size[1], 1))
    pw, ph = size[0] * scale, size[1] * scale
    return (x + (w - pw) / 2, y + (h - ph) / 2, pw, ph)


class Slide:
    def __init__(self, deck: "Deck") -> None:
        self.deck = deck
        self.shapes: List[str] = []
        self.images: List[bytes] = []
        self._next_id = 2

    def text(self, x: float, y: float, w: float, h: float, content: Union[str, Sequence[Paragraph]], *,
             size: float = 12, bold: bool = False, color: str = "1F2A44", font: str = "Calibri",
             valign: str = "t", shrink: bool = False) -> None:
        """A text box at (x, y) of (w, h) inches. `content` is a string,
        each line a paragraph in the box's own size, weight and color, or a
        list of paragraphs, each a list of (text, options) runs whose
        options may say `bold`, `color` and `size`."""
        if isinstance(content, str):
            paragraphs: List[Paragraph] = [[(line, {})] for line in content.split("\n")]
        else:
            paragraphs = [list(p) for p in content]
        body = []
        for paragraph in paragraphs:
            runs = []
            for text, options in paragraph:
                run_size = int(round(float(options.get("size", size)) * 100))
                run_bold = ' b="1"' if options.get("bold", bold) else ""
                run_color = str(options.get("color", color))
                runs.append('<a:r><a:rPr lang="en-US" sz="%d"%s dirty="0"><a:solidFill><a:srgbClr val="%s"/>'
                            '</a:solidFill><a:latin typeface="%s"/></a:rPr><a:t>%s</a:t></a:r>'
                            % (run_size, run_bold, run_color, escape(font), escape(text)))
            if not runs:
                runs.append('<a:endParaRPr lang="en-US" sz="%d"/>' % int(round(size * 100)))
            body.append("<a:p>%s</a:p>" % "".join(runs))
        shape_id = self._next_id
        self._next_id += 1
        self.shapes.append(
            '<p:sp><p:nvSpPr><p:cNvPr id="%d" name="TextBox %d"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            '<p:txBody><a:bodyPr wrap="square" anchor="%s" lIns="0" tIns="0" rIns="0" bIns="0">%s</a:bodyPr>'
            '<a:lstStyle/>%s</p:txBody></p:sp>'
            % (shape_id, shape_id - 1, _emu(x), _emu(y), _emu(w), _emu(h), "ctr" if valign == "ctr" else "t",
               "<a:normAutofit/>" if shrink else "", "".join(body)))

    def image(self, png: bytes, x: float, y: float, w: float, h: float) -> None:
        """A PNG at (x, y) of (w, h) inches, as given; `fitted` keeps the
        aspect for the caller."""
        self.images.append(png)
        rel = "rId%d" % (len(self.images) + 1)  # rId1 is the layout
        shape_id = self._next_id
        self._next_id += 1
        self.shapes.append(
            '<p:pic><p:nvPicPr><p:cNvPr id="%d" name="Picture %d"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/>'
            '</p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/>'
            '</a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
            % (shape_id, shape_id - 1, rel, _emu(x), _emu(y), _emu(w), _emu(h)))

    @property
    def next_id(self) -> int:
        """The id the next shape on this slide gets; `shapes_xml` takes
        them from here."""
        return self._next_id

    def shapes_xml(self, elements: Sequence[str]) -> None:
        """Shapes written elsewhere (`terrane.draw.dml`), one element each,
        with ids taken from `next_id` in order."""
        self.shapes.extend(elements)
        self._next_id += len(elements)

    def xml(self) -> str:
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sld %s><p:cSld><p:spTree>%s%s</p:spTree>'
                '</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
                % (NS, EMPTY_TREE, "".join(self.shapes)))

    def rels(self, first_image: int) -> str:
        rels = ['<Relationship Id="rId1" Type="%sslideLayout" Target="../slideLayouts/slideLayout1.xml"/>' % REL]
        for i in range(len(self.images)):
            rels.append('<Relationship Id="rId%d" Type="%simage" Target="../media/image%d.png"/>'
                        % (i + 2, REL, first_image + i))
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships '
                'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>' % "".join(rels))


class Deck:
    """A presentation of blank slides, `WIDE` by default."""

    def __init__(self, title: str, size: Tuple[float, float] = WIDE) -> None:
        self.title = title
        self.size = size
        self.slides: List[Slide] = []

    def slide(self) -> Slide:
        slide = Slide(self)
        self.slides.append(slide)
        return slide

    def parts(self) -> List[Tuple[str, bytes]]:
        """Every part of the file, in a fixed order."""
        n = len(self.slides)
        parts: List[Tuple[str, bytes]] = []
        overrides = [
            ("/ppt/presentation.xml", "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"),
            ("/ppt/slideMasters/slideMaster1.xml", "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"),
            ("/ppt/slideLayouts/slideLayout1.xml", "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"),
            ("/ppt/theme/theme1.xml", "application/vnd.openxmlformats-officedocument.theme+xml"),
            ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
            ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml"),
        ] + [("/ppt/slides/slide%d.xml" % (i + 1),
              "application/vnd.openxmlformats-officedocument.presentationml.slide+xml") for i in range(n)]
        parts.append(("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
            + "".join('<Override PartName="%s" ContentType="%s"/>' % o for o in overrides) + "</Types>").encode("utf-8")))
        parts.append(("_rels/.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="%sofficeDocument" Target="ppt/presentation.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/'
            'core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="%sextended-properties" Target="docProps/app.xml"/></Relationships>'
            % (REL, REL)).encode("utf-8")))
        parts.append(("docProps/core.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>%s</dc:title><dc:creator>architecture-as-code</dc:creator></cp:coreProperties>'
            % escape(self.title)).encode("utf-8")))
        parts.append(("docProps/app.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<Application>architecture-as-code</Application><Slides>%d</Slides></Properties>' % n).encode("utf-8")))
        slide_ids = "".join('<p:sldId id="%d" r:id="rId%d"/>' % (256 + i, i + 2) for i in range(n))
        parts.append(("ppt/presentation.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:presentation %s saveSubsetFonts="1">'
            '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
            '<p:sldIdLst>%s</p:sldIdLst><p:sldSz cx="%d" cy="%d"/><p:notesSz cx="6858000" cy="9144000"/>'
            '<p:defaultTextStyle><a:defPPr><a:defRPr lang="en-US"/></a:defPPr></p:defaultTextStyle></p:presentation>'
            % (NS, slide_ids, _emu(self.size[0]), _emu(self.size[1]))).encode("utf-8")))
        rels = ['<Relationship Id="rId1" Type="%sslideMaster" Target="slideMasters/slideMaster1.xml"/>' % REL]
        rels += ['<Relationship Id="rId%d" Type="%sslide" Target="slides/slide%d.xml"/>' % (i + 2, REL, i + 1)
                 for i in range(n)]
        rels.append('<Relationship Id="rId%d" Type="%stheme" Target="theme/theme1.xml"/>' % (n + 2, REL))
        parts.append(("ppt/_rels/presentation.xml.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>'
            % "".join(rels)).encode("utf-8")))
        parts.append(("ppt/slideMasters/slideMaster1.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sldMaster %s><p:cSld><p:bg><p:bgRef idx="1001">'
            '<a:schemeClr val="bg1"/></p:bgRef></p:bg><p:spTree>%s</p:spTree></p:cSld>'
            '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
            'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
            '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
            '<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="4400"/></a:lvl1pPr></p:titleStyle>'
            '<p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:bodyStyle>'
            '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:otherStyle></p:txStyles></p:sldMaster>'
            % (NS, EMPTY_TREE)).encode("utf-8")))
        parts.append(("ppt/slideMasters/_rels/slideMaster1.xml.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="%sslideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
            '<Relationship Id="rId2" Type="%stheme" Target="../theme/theme1.xml"/></Relationships>'
            % (REL, REL)).encode("utf-8")))
        parts.append(("ppt/slideLayouts/slideLayout1.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sldLayout %s type="blank" preserve="1">'
            '<p:cSld name="Blank"><p:spTree>%s</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>'
            '</p:sldLayout>' % (NS, EMPTY_TREE)).encode("utf-8")))
        parts.append(("ppt/slideLayouts/_rels/slideLayout1.xml.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="%sslideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>'
            % REL).encode("utf-8")))
        parts.append(("ppt/theme/theme1.xml", THEME.encode("utf-8")))
        image_no = 1
        for i, slide in enumerate(self.slides):
            parts.append(("ppt/slides/slide%d.xml" % (i + 1), slide.xml().encode("utf-8")))
            parts.append(("ppt/slides/_rels/slide%d.xml.rels" % (i + 1), slide.rels(image_no).encode("utf-8")))
            for png in slide.images:
                parts.append(("ppt/media/image%d.png" % image_no, png))
                image_no += 1
        return parts

    def to_bytes(self) -> bytes:
        import io
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in self.parts():
                info = zipfile.ZipInfo(name, date_time=STAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                # The same bytes on every platform; see render_excel.
                info.create_system = 0
                zf.writestr(info, data)
        return buffer.getvalue()

    def save(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_bytes())
        return path


THEME = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Terrane"><a:themeElements>'
    '<a:clrScheme name="Terrane"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
    '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F2A44"/></a:dk2>'
    '<a:lt2><a:srgbClr val="F3F5FB"/></a:lt2><a:accent1><a:srgbClr val="3D4FA3"/></a:accent1>'
    '<a:accent2><a:srgbClr val="0A6CFF"/></a:accent2><a:accent3><a:srgbClr val="6D28D9"/></a:accent3>'
    '<a:accent4><a:srgbClr val="0369A1"/></a:accent4><a:accent5><a:srgbClr val="B91C1C"/></a:accent5>'
    '<a:accent6><a:srgbClr val="4D7C0F"/></a:accent6><a:hlink><a:srgbClr val="0A6CFF"/></a:hlink>'
    '<a:folHlink><a:srgbClr val="7B8798"/></a:folHlink></a:clrScheme>'
    '<a:fontScheme name="Terrane"><a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/>'
    '</a:majorFont><a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>'
    '</a:fontScheme><a:fmtScheme name="Terrane"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '</a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="38100"><a:solidFill>'
    '<a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/>'
    '</a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle>'
    '</a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill>'
    '<a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
    '</a:fmtScheme></a:themeElements></a:theme>'
)
