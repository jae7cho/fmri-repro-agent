# Spike: JATS XML and GROBID against the PDF text layer (2026-11-06)

## Versions and wall time

- Docker Desktop 4.98.0 (Docker Engine 29.9.2), Apple Silicon host. The container has 16 CPUs and
  8.3 GB of memory.
- GROBID 0.9.1 (`/api/version`: 0.9.1). There is no plain `lfoppiano/grobid:0.9.1` tag on Docker Hub;
  the 0.9.1 release is published as `0.9.1-full` and `0.9.1-crf`.
  - Used: `lfoppiano/grobid:0.9.1-full`, run with `--platform linux/amd64`, which worked as given. The
    image is 37.4 GB.
  - `/api/isalive` returned true about 30 s after start.
- `/api/processFulltextDocument`, one request per PDF:

| paper | wall time | TEI size |
|---|---|---|
| gordon_2014 (first request after start) | 34.6 s | 117,311 bytes |
| cattarinussi_2026 | 8.1 s | 145,597 bytes |

## Europe PMC coverage, 19 corpus papers

How the rows were filled:
- **DOI.** Each DOI came from the PDF's Info or XMP metadata, or from its page-1 DOI lines
  (`doi_date_resolver._page1_dois`); nothing past page one was read. DOIs were held in memory only.
- **Matching.** A DOI was accepted when the Europe PMC record had the paper id's first-author surname
  and year.
- **Requests.** The REST `search` endpoint (`resultType=core`), then `fullTextXML` for records with a
  PMCID. The client name was generic, with no email.
- **Version** is Europe PMC's author-manuscript flag (`authMan`) on records with XML.

| paper | DOI from | in OA subset | XML available | version | journal |
|---|---|---|---|---|---|
| agtzidis_2020 | Info metadata | no | no | — | NeuroImage |
| binder_1999 | none on page 1 or in metadata | — | — | — | — |
| braun_2015 | XMP | no | no | — | PNAS |
| chen_2015 | XMP | yes | yes | version of record | PLoS One |
| ciric_2017 | page 1 | no | no | — | NeuroImage |
| cole_2013 | page 1 | yes | yes | author manuscript | Nature Neuroscience |
| derosa_2025 | Info metadata | yes | yes | version of record | NeuroImage: Clinical |
| gordon_2014 | Info metadata | no | no | — | Human Brain Mapping |
| liu_2005 | page 1 | no | no | — | Neuron |
| liu_2013 | page 1 | yes | yes | version of record | Frontiers in Systems Neuroscience |
| mueller_2021 | XMP | yes | yes | version of record | Network Neuroscience |
| oconnor_2017 | page 1 | yes | yes | version of record | GigaScience |
| poldrack_2015 | Info metadata | yes | yes | version of record | Nature Communications |
| power_2014 | page 1 | no | no | — | NeuroImage |
| tang_2025 | Info metadata | yes | yes | version of record | Scientific Reports |
| vanderwal_2016 | page 1 | no | no | — | bioRxiv |
| viduarre_2017 | XMP | yes | yes | version of record | PNAS |
| weber_2024 | Info metadata | yes | yes | version of record | Molecular Autism |
| wheaton_2004 | page 1 | no | no | — | NeuroImage |

Counts:
- **XML available:** 10 of 19 (9 version of record, 1 author manuscript).
- **In PMC but not in the OA subset, so no XML:** 5 (braun_2015, ciric_2017, gordon_2014, liu_2005,
  power_2014).
- **In Europe PMC but not in PMC:** 3 (agtzidis_2020, vanderwal_2016, wheaton_2004).
- **No DOI found on page 1 or in the metadata:** 1 (binder_1999).
- Neither known quote failure (gordon_2014, cattarinussi_2026) has JATS. cattarinussi_2026 is not
  among the 19; gordon_2014 has no XML.

## GROBID on the two known quote failures

**(a) gordon_2014's band-pass sentence: yes.** It comes out in one `<p>` as one contiguous string,
from its first word to its citation. It contains no running header: no author line, no page number,
and "signal" is followed directly by "variation". In the PDF text layer, the page header sits
between those two words.

**(b) cattarinussi_2026's inline citation numbers: yes.**
- They come out as `<ref type="bibr">` elements: 69 in the body, 7 in the preprocessing paragraph.
- The number the text layer puts before "Briefly" is a `<ref>` here.
- If the body is flattened with the `<ref>` text kept, the digits are back in the prose, and the 11
  quotes that fail on the text layer still fail (11 of 11 not found).
- With the `<ref>` elements removed, 11 of 11 resolve.

**(c) The three stored gordon_2014 filtering quotes against the TEI body text** (each `<head>` and
`<p>` on its own line), using `span_resolver.resolve_quote`:

| quote | found |
|---|---|
| `temporal_filtering.performed` | found |
| `temporal_filtering.effective_band_hz` | found |
| `temporal_filtering.relative_to_regression` | found |

On the PDF text layer, all three are not found (DEVLOG 2026-11-06).

**(d) `<head>` tags for methods slicing.**
- **Structure:** the body is a flat list of `<div>`, each with one `<head>`, with no nested `<div>`
  and no `n` attribute on any head (gordon_2014: 27 divs, 34 heads; cattarinussi_2026: 16 divs, 20
  heads).
  - Section level is therefore not given; METHODS and its subsections are siblings.
  - The references are in `<back>`, outside the body.
- **Heads that are not sections:**
  - Figure and table captions appear as heads: 3 in gordon_2014, 4 in cattarinussi_2026.
  - gordon_2014 also has 4 heads reading "r" (a journal glyph), and one section title split over two
    heads.
- **Our heuristic (`find_methods_section`) on the TEI body text, versus on the PDF text layer:**

| paper | source | header | ends at | characters | share of text |
|---|---|---|---|---|---|
| gordon_2014 | TEI body | METHODS | RESULTS | 13,759 | 0.336 |
| gordon_2014 | PDF text layer | METHODS | DISCUSSION | 25,592 | 0.425 |
| cattarinussi_2026 | TEI body | Methods | Results | 11,111 | 0.281 |
| cattarinussi_2026 | PDF text layer, reflowed | "32\nMethods" | Results | 13,168 | 0.194 |

  - On the TEI body, gordon_2014's slice ends at RESULTS; on the text layer it runs on to
    DISCUSSION.
  - cattarinussi_2026's matched header has no citation number in front of it.
  - Neither needed reflow.
