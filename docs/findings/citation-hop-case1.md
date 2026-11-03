# The citation hop, case one: gracia-tabuenca_2024 -> Hagler et al. (2019) (2026-11-03)

Values read in Hagler et al. (2019) are withheld until the author records the key (the author's
instruction, 2026-11-03). This file records what was asked and how it resolved.

## The build

`citation_hop.py` and its script, per `docs/design/DESIGN_citation_hop.md` ("As built for case
one"). Tests: 613 extractor (not live), 235 root; hooks clean. Mutations, each with a non-empty
diff shown before the run:

| mutation | result |
|---|---|
| an ambiguous reference picks one entry | killed |
| the scope asks rows the citing paper reports | killed |
| a variant's quote is never checked | killed |
| a variant outside the scope is kept | **survived** first: the test's out-of-scope variant named no real field, so the check was never reached. The test now uses `spatial_smoothing.fwhm_mm`; killed |
| two matching local PDFs pick one | killed |
| fork E's filter removed | killed |
| the second-hop section not rendered | killed |
| a generational-suffix strip removed | **survived**: the first-word key already covers it, so the strip was removed as redundant |
| the first-word key replaced by the last word | killed |

Identity gate, derived first (no stored record carries a hop, and fork E changes extraction only,
so nothing changes): a1 19 identical, v2 19, v3 18, v4 18, against HEAD; negative control against
`d31e8b7`: 0 of 19 identical.

## The run

`results/hop_case1/` (gitignored): `gracia-tabuenca_2024.second_hop.json` and the report re-rendered
with the second-hop section. Model as coverage_v4.

- **First run (09:35 ET): `reference_not_found`, 0 model calls.** The first author parsed as
  "Hagler Jr" and the matcher compared the last word. Fixed as above.
- **Second run (09:36–09:38 ET):** reference entry resolved; target a local PDF
  (`tested_lit/sfn_batch/Hagler_2019.pdf`), with the entry's DOI found on the PDF; the cited
  methods slice found by its heading. The checking pass returned ok.

**Fields asked: 23**, plus the software list (fork A: the base pipeline is deferred to Hagler). One
because it is deferred to Hagler: `distortion_correction.method`. The rest because the citing paper
does not report the row: brain extraction (4 fields), slice-time correction (6), coregistration (6),
spatial smoothing (6). No asked row fell outside calls T and S.

| call | wall (s) | input tokens | output tokens | cost (USD, LiteLLM price table) |
|---|---|---|---|---|
| T | 10.7 | 19,931 | 971 | 0.0818 |
| S | 26.2 | 19,195 | 2,187 | 0.0994 |
| checking pass, first attempt | 43.9 | 17,957 | 3,591 | 0.1185 |
| checking pass, retry | 25.1 | 25,877 | 3,372 | 0.1410 |
| **all** | **107.3** (hop) | **82,960** | **10,121** | **0.4408** |

The checking pass took two model calls inside one `create()`. instructor makes a second call
(`max_retries=2`) when a response fails validation; the failed response itself was not recorded, so
the cause is inferred from the call count. Both calls are billed and both are counted.
