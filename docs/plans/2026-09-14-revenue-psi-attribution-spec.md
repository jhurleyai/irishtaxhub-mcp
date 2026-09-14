# Revenue PSI Licence attribution — spec

**Date:** 2026-09-14
**Status:** Draft for Codex review
**Scope:** irishtaxhub-mcp, irishtaxhub (web), irishtaxhubapi, irishtaxhub-lambdas, irishtaxhubplatform

## 1. Why

Irish Tax Hub scrapes Revenue's Tax & Duty Manuals, Notes for Guidance, legislation pages,
eBriefs and double-taxation treaty PDFs from revenue.ie, extracts the text, indexes it, sends
excerpts to Claude for titles/summaries/keywords, and serves the text and metadata through a
public MCP server (ChatGPT app and Claude connector), a public REST API, the website, and the
platform's tax chat. The same corpus also holds 26 gov.ie PRSI guides (SW14) seeded from
`prsi_seed.json`.

Revenue publishes its material under its Public Sector Information Licence (PSI Licence),
which conforms to CC BY 4.0. McCann FitzGerald confirmed on 2026-09-14 that the use is
permitted **provided the licence's attribution notice is included**, and that sending excerpts
to Claude is permitted but attribution is "still technically required" there too.

An audit on 2026-09-14 found no surface carries the notice. This spec closes that gap with the
smallest change per surface.

## 2. Licence requirements (verbatim, from the PSI Licence PDF)

Users must "Acknowledge the source of the Information by including the following attribution
statement:

> Information provided courtesy of the Revenue Commissioners under a Creative Commons
> Attribution 4.0 International (CC BY 4.0) licence

and, where possible, provide a link to this licence."

Where multiple attributions are not practical for a product that uses several public sector
sources, the alternative is:

> Contains Irish Public Sector Information licensed under a Creative Commons Attribution 4.0
> International (CC BY 4.0) licence

Other conditions: no use of Revenue's names, crests, logos or official symbols; nothing that
suggests official status or Revenue endorsement; rights end automatically on breach. CC BY 4.0
additionally requires indicating if the material was modified.

## 3. Constants

Each repo defines the constants it uses, with exactly these values. There is no shared package
and no cross-repo check; each repo's tests assert its own constant equals the literal here.

| Name | Value |
|---|---|
| `REVENUE_ATTRIBUTION_STATEMENT` | `Information provided courtesy of the Revenue Commissioners under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence` |
| `PSI_MULTI_SOURCE_STATEMENT` | `Contains Irish Public Sector Information licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence` |
| `REVENUE_LICENCE_URL` | `https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/public-sector-information-licence.pdf` |
| `REVENUE_PSI_INFO_URL` | `https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/index.aspx` |
| `CC_BY_4_URL` | `https://creativecommons.org/licenses/by/4.0/` |
| `REVENUE_TDM_INDEX_URL` | `https://www.revenue.ie/en/tax-professionals/tdm/index.aspx` |
| `REVENUE_TREATIES_INDEX_URL` | `https://www.revenue.ie/en/tax-professionals/tax-agreements/double-taxation-treaties/tax-treaties-by-country.aspx` |
| `REVENUE_EBRIEF_INDEX_URL` | `https://www.revenue.ie/en/tax-professionals/ebrief/index.aspx` |
| `MODIFICATION_NOTE` | `Irish Tax Hub has reformatted this material: document text is extracted from the original PDF or page, and descriptions, keywords and groupings are Irish Tax Hub's own. Refer to the original at source_url.` |

The statement has no trailing full stop inside JSON fields. In prose (web pages, prompts) a full
stop follows it.

## 4. The attribution object

One JSON shape, produced by the API and passed through by the MCP server:

```json
{
  "provider": "Revenue Commissioners",
  "statement": "Information provided courtesy of the Revenue Commissioners under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence",
  "licence": "CC BY 4.0",
  "licence_url": "https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/public-sector-information-licence.pdf",
  "source_url": "https://www.revenue.ie/en/tax-professionals/tdm/income-tax-capital-gains-tax-corporation-tax/part-19/19-07-03.pdf",
  "modified": true,
  "modification_note": "Irish Tax Hub has reformatted this material: ... Refer to the original at source_url."
}
```

`source_url` is the specific document URL when the response is about one document, otherwise
the relevant revenue.ie index page (TDM index, treaty index, eBrief index). `modified` is always
`true`.

**gov.ie records.** The corpus is Revenue material plus 26 gov.ie PRSI guides. Collection
responses (search, categories, changelog) carry the Revenue object at the top level: Revenue's
licence asks for its specific statement wherever practical, and the collection is
overwhelmingly Revenue's. Each gov.ie result is identifiable by its `category`
(`PRSI (gov.ie)`) and, once item 4 ships, carries its own `attribution` and `licenceUrl`
fields, which consumers are told to prefer. A single-document text response is attributed by
`attribution_for(record)` (section 5.3): a gov.ie record, recognised by its category or URL
host, gets `provider: "Department of Social Protection (gov.ie)"`, the multi-source statement
and `licence_url: CC_BY_4_URL`; stored provenance fields (section 5.4) override the derived
values when present; everything else gets the Revenue object.

## 5. Per-repo requirements

### 5.1 irishtaxhub-mcp (item 1, ships first, this week)

Files: `src/irishtaxhub_mcp/attribution.py`, `src/irishtaxhub_mcp/server.py`,
`tests/test_server.py`, `tests/test_tax_treaties_tools.py`, new `tests/test_revenue_tools.py`,
`README.md`, `chatgpt-app-submission.json`, `docs/sample-questions.md`.

1. Constants from section 3 in `attribution.py` (statement, licence URL, three index URLs,
   modification note) and `revenue_source(source_url: str) -> dict` returning the section 4
   object.
2. `_with_attribution` gains keyword-only `source: Optional[dict] = None`. Resolution order:
   - if the upstream `result` dict has a top-level `attribution` dict containing a `statement`
     key (the API after item 3), that dict is **moved** to `attribution.source` and the
     top-level `attribution` key becomes the Irish Tax Hub block as today;
   - else if `source` was passed, it becomes `attribution.source`;
   - else no `source` key (calculator, constants, key-dates, stats tools are unchanged).
   When `source` is present, `last_updated_note` is
   `"Date this response was generated. Source material is as last retrieved from the source identified in attribution.source."`
   Otherwise the existing note is unchanged.
3. The seven Revenue-derived tools pass `source=`:
   - `search_revenue_documents`, `list_revenue_document_categories`:
     `revenue_source(REVENUE_TDM_INDEX_URL)`
   - `get_revenue_ebrief_changelog`: `revenue_source(REVENUE_EBRIEF_INDEX_URL)`
   - `get_revenue_document_text`: `revenue_source(result.get("url") or REVENUE_TDM_INDEX_URL)`;
     the 404 branch passes `revenue_source(REVENUE_TDM_INDEX_URL)`.
   - `search_tax_treaties`, `list_tax_treaty_countries`:
     `revenue_source(REVENUE_TREATIES_INDEX_URL)`
   - `get_tax_treaty_text`: as the Revenue text tool with `REVENUE_TREATIES_INDEX_URL`.
4. `_ATTRIBUTION_SCHEMA` gains an optional `source` object property (`additionalProperties:
   true`). `required` unchanged. `_DOCUMENT_TEXT_OUTPUT_SCHEMA` gains optional `url`, `title`,
   `displayName` strings (present once item 3 ships).
5. `FastMCP("irishtaxhub-mcp", instructions=SERVER_INSTRUCTIONS)` with `SERVER_INSTRUCTIONS`
   in `server.py`:

   > Irish Tax Hub tools return Irish tax calculations and reference material. The Revenue
   > document, eBrief and tax-treaty tools return material published by the Office of the
   > Revenue Commissioners (revenue.ie) and reused under Revenue's Public Sector Information
   > Licence (CC BY 4.0). When your answer relies on that material: include the statement
   > "Information provided courtesy of the Revenue Commissioners under a Creative Commons
   > Attribution 4.0 International (CC BY 4.0) licence"; link to the original document using
   > the result's `url` field or `attribution.source.source_url`; and note that document text
   > is extracted from the original and that descriptions and keywords are Irish Tax Hub's own.
   > A few records come from gov.ie rather than Revenue (category "PRSI (gov.ie)"); where a
   > result carries its own `attribution` and `licenceUrl` fields, reproduce those instead.
   > Do not present Irish Tax Hub or its tools as official or endorsed by Revenue.

6. The seven tool docstrings gain a final line:
   `Content is reused from public sector sources, normally revenue.ie under Revenue's PSI Licence (CC BY 4.0); reproduce the result's own attribution where present, otherwise attribution.source.statement, when citing.`
7. Tests:
   - existing `test_attributed_result_exposes_links_in_structured_content_and_content_blocks`
     is unchanged except it additionally asserts `"source" not in attribution`;
   - new: `revenue_source()` returns the exact statement and URLs; `_with_attribution(source=
     ...)` places it under `attribution.source` in `structured_content`, in `content[0]` JSON
     and in `meta`; an upstream `attribution` with `statement` is moved to `source` and the
     top-level block still has `provider == "Irish Tax Hub"`; each of the seven tools yields
     `attribution.source.statement == REVENUE_ATTRIBUTION_STATEMENT` and the expected
     `source_url` (mock `_get_client_and_loader` as the treaty tests do); a
     `get_revenue_document_text` call whose mocked API response carries a gov.ie
     `attribution` (provider `Department of Social Protection (gov.ie)`, multi-source
     statement, CC BY URL) keeps those values in `attribution.source` in `structured_content`,
     `content[0]` JSON and `meta`, with no Revenue statement anywhere in the result;
     `_with_attribution` with no source has no `source` key; `mcp.instructions` contains the
     statement; `REVENUE_ATTRIBUTION_STATEMENT` equals the section 3 literal.
8. `README.md`: "Source material and licensing" section after "Tools" with the statement, the
   licence link and the modification note. `chatgpt-app-submission.json`: the seven Revenue and
   treaty `read_only_justification` strings end with "Content is reused under Revenue's PSI
   Licence (CC BY 4.0) with attribution in every response."; the two document test cases'
   `expected_output` end with "and Revenue PSI Licence attribution". `docs/sample-questions.md`:
   remove the stale `generate_net_income_summary` section, add one line noting the attribution
   in Revenue results.

Deploy: merge to `main` runs `deploy-stage`; production is a manual `deploy-prod` dispatch.
Verify on stage with one real `get_revenue_document_text` call.

### 5.2 irishtaxhub web (item 2, ships this week)

Files: new `apps/web/src/components/RevenueAttribution.tsx` and `.test.tsx`,
`apps/web/src/app/(marketing)/revenue-documents/RevenueDocumentsSearch.tsx`,
`apps/web/src/app/(marketing)/mcp/page.tsx`, `apps/web/src/components/Footer.tsx`.

1. `RevenueAttribution` component, prop `variant: "full" | "compact"`, no emoji, muted DaisyUI
   text. `full` renders:
   - the statement as a sentence, with "Creative Commons Attribution 4.0 International (CC BY
     4.0) licence" linked to `REVENUE_LICENCE_URL` (new tab, `rel="noopener noreferrer"`), then
     a link "About Revenue's re-use policy" to `REVENUE_PSI_INFO_URL`;
   - a second sentence: "Document text is extracted from the original PDFs and may differ in
     layout; descriptions and keywords are written by Irish Tax Hub. PRSI guides are published
     by the Department of Social Protection on gov.ie under CC BY 4.0. Always check the
     original document. Irish Tax Hub is not affiliated with or endorsed by Revenue."
   `compact` renders the first sentence only.
2. Revenue documents page: `<RevenueAttribution variant="full" />` directly under the intro
   paragraph in `RevenueDocumentsSearch`, visible on both tabs.
3. MCP page: hero paragraph becomes
   "Connect Claude directly to Irish tax tools and reference material. Irish Tax Hub exposes
   its tax calculators, current tax constants and key dates, together with Revenue's Tax & Duty
   Manuals and Ireland's double-taxation treaties (reused under Revenue's PSI Licence), as Model
   Context Protocol (MCP) tools, so answers are grounded in live data for the current tax year
   rather than the model's training. All tools are read-only."
   Remove "authoritative" from the page `description` metadata. New section "Source material
   and licensing" after "Data and privacy" containing `<RevenueAttribution variant="full" />`
   and the sentence "Every Revenue-derived tool result carries this attribution in its
   attribution.source field."
4. Footer: one line above the copyright line, same muted style: "Contains Irish Public Sector
   Information licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0)
   licence." with "CC BY 4.0" linked to `CC_BY_4_URL`. This is the multi-source statement
   because the site also reuses gov.ie PRSI guides and other public sector material.
5. Test: `RevenueAttribution.test.tsx` (vitest + testing-library) asserts the statement text
   and both `href` values in `full`, and that `compact` omits the second sentence.

Deploy: merge builds a Vercel preview; promote the `main` build in the Vercel dashboard by hand.

### 5.3 irishtaxhubapi (item 3)

Files: new `irishtaxhubapi/schemas/attribution.py`, `irishtaxhubapi/schemas/revenue_docs.py`,
`irishtaxhubapi/schemas/tax_treaties.py`, `irishtaxhubapi/routers/v1.py` (Revenue and treaty
sections), `irishtaxhubapi/facades/revenue_docs/facade.py`,
`irishtaxhubapi/facades/tax_treaties/facade.py`, new `tests/views/test_revenue_docs_routes.py`,
`tests/views/test_tax_treaties_routes.py`, `tests/facades/test_revenue_docs.py`,
`tests/facades/test_tax_treaties.py`.

1. `schemas/attribution.py`: section 3 constants (statement, multi-source statement, licence
   URL, CC BY URL, three index URLs, modification note), a `RevenueAttribution` pydantic model
   with the seven section 4 fields, `revenue_attribution(source_url: str) -> RevenueAttribution`,
   and `attribution_for(record: dict) -> RevenueAttribution` which returns the Revenue object
   with `source_url = record["url"]`, except for gov.ie records, which get `provider`
   `Department of Social Protection (gov.ie)`, the multi-source statement and
   `licence_url = CC_BY_4_URL`. A record is gov.ie when its `category` is `PRSI (gov.ie)` or
   its URL host is `gov.ie` or ends with `.gov.ie`; if the record already carries
   `sourceOrganisation`, `attribution` and `licenceUrl` (written by item 4) those values win.
   The API therefore attributes gov.ie records correctly from day one, before item 4 ships.
2. Response models gain `attribution: RevenueAttribution`: `RevenueDocsSearchResponse`,
   `RevenueCategoryResponse`, `EbriefChangelogResponse`, `RevenueDocumentTextResponse`,
   `TaxTreatySearchResponse`, `TaxTreatyCountryResponse`, `TaxTreatyTextResponse`. Text
   responses also gain `url: str = ""`, `title: str = ""`, `displayName: str = ""`.
   `RevenueDocument` and `TaxTreaty` gain optional `sourceOrganisation: str = ""`,
   `attribution: str = ""` and `licenceUrl: str = ""` so per-record provenance from item 4
   passes through instead of being stripped by the response model.
3. Facades gain `get_document(filename)` (Revenue) and `get_treaty(filename)` (treaties):
   normalise `filename` by taking the last path segment, dropping any query/fragment, and
   stripping a case-insensitive `.pdf`; return the first record from `_load_docs()` whose
   `_text_url_for(record["url"])` last segment equals it, else `None`. Pure in-memory.
4. Routers set `attribution` explicitly:
   - search, categories: `revenue_attribution(REVENUE_TDM_INDEX_URL)`
   - changelog: `revenue_attribution(REVENUE_EBRIEF_INDEX_URL)`
   - Revenue text: record found → `url`, `title`, `displayName` from the record and
     `attribution_for(record)`; not found → empty strings and
     `revenue_attribution(REVENUE_TDM_INDEX_URL)`.
   - treaty search, countries: `revenue_attribution(REVENUE_TREATIES_INDEX_URL)`
   - treaty text: as Revenue text with the treaty index fallback.
   The 404 `JSONResponse` bodies are unchanged.
5. OpenAPI: each of the seven routes' `description` gains "Content is reused from revenue.ie
   under Revenue's Public Sector Information Licence (CC BY 4.0); every successful response
   carries an `attribution` object whose `statement` must be reproduced when the content is
   displayed. Individual results may carry their own `attribution` and `licenceUrl` where the
   source is not Revenue."
6. Tests: route tests for all seven endpoints assert `attribution.statement` and `source_url`;
   the Revenue text route with a `PRSI (gov.ie)` record (no stored provenance fields) returns
   the gov.ie provider, multi-source statement and CC BY URL, and with stored fields returns
   those; facade tests for `get_document` / `get_treaty` (found, not found, `19-07-03.PDF`, a
   Notes-for-Guidance compound stem); existing `test_search_endpoint` keeps `source == "s3"`.

Deploy: merge runs `deploy-stage`; production manual. Ship after 5.1 is on production so the
MCP fallback is live; the MCP server then adopts the API object automatically.

### 5.4 irishtaxhub-lambdas (item 4)

Files: new `lambda/revenue_docs/rescrape/provenance.py`, `rescrape/Dockerfile` (add
`provenance.py` to the `COPY` line), `rescrape/corpus.py`, `rescrape/common.py`,
`rescrape/app.py`, `rescrape/enrichment.py`, `rescrape/treaties.py`, `rescrape/algolia_index.py`,
`lambda/revenue_docs/ebrief_monitor/app.py`, `scripts/enrich-metadata.py`, tests
`tests/test_provenance.py`, `tests/test_rescrape_crawl.py`, `tests/test_treaties.py`,
`tests/test_ebrief_monitor.py`, `tests/test_algolia_index.py`, `README.md`,
`docs/revenue-documents-algolia-search.md`.

1. `provenance.py` (rescrape package): section 3 constants and
   - `PROMPT_ATTRIBUTION_PREAMBLE`:
     `The excerpts below are extracts from documents published by the Office of the Revenue Commissioners (revenue.ie), reused under Revenue's Public Sector Information Licence (CC BY 4.0). Attribution: "Information provided courtesy of the Revenue Commissioners under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence". Licence: https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/public-sector-information-licence.pdf`
   - `REVENUE_PROVENANCE = {"sourceOrganisation": "Revenue Commissioners", "licence": "CC BY 4.0", "licenceUrl": REVENUE_LICENCE_URL, "attribution": REVENUE_ATTRIBUTION_STATEMENT}`
   - `GOV_IE_PROVENANCE = {"sourceOrganisation": "Department of Social Protection (gov.ie)", "licence": "CC BY 4.0", "licenceUrl": CC_BY_4_URL, "attribution": PSI_MULTI_SOURCE_STATEMENT}`
   - `provenance_for(record: dict) -> dict`: `GOV_IE_PROVENANCE` when
     `record.get("category") == "PRSI (gov.ie)"` or the URL host is `gov.ie` or ends with
     `.gov.ie` (two seeds are `web.archive.org` captures, hence the category check first);
     else `REVENUE_PROVENANCE`.
   - `stamp(records: Iterable[dict], retrieved_at: str) -> list[dict]`: returns copies with the
     four provenance keys from `provenance_for(record)` and `retrievedAt = retrieved_at`.
   - `text_object_metadata(record: dict) -> dict`: S3 `Metadata` with `source-url`, `licence`,
     `licence-url`, `attribution` from `provenance_for(record)`. All values ASCII. Crawl and
     eBrief callers, which only have a revenue.ie URL, pass `{"url": url}`; the seed path
     (`backfill_seed_text` → `_save_seed_text_strict`) passes the full seed record so the two
     `web.archive.org` seeds are stamped gov.ie.
2. Corpus records are stamped once per corpus, before both persistence and indexing. In
   `app.main()`: `docs_list = stamp(updated_docs.values(), run_timestamp)` after
   `merge_seed_docs`, then `save_docs` writes that list and `index_documents` indexes the same
   list. In `treaties.run()`: stamp `merged` before `save_treaties` and the treaty index push.
   `run_timestamp` is one ISO-8601 UTC timestamp computed at the start of `main()` and passed
   to `treaties.run`. `retrievedAt` therefore means "last confirmed on the source site by this
   crawl"; every record gets it on the first run after deploy. `CANONICAL_DOC_FIELDS` and seed
   validation are unchanged; `save_docs` accepts a list as well as the dict it takes today.
3. Text objects: `save_text`, `_save_seed_text_strict` (signature becomes
   `(s3_client, record, text)`), `save_treaty_text` and the eBrief monitor's `save_text_to_s3`
   pass `Metadata=text_object_metadata(...)`. The text body is unchanged. Existing objects gain
   metadata only when rewritten; no backfill.
4. Algolia: `build_records` copies `sourceOrganisation`, `licence`, `licenceUrl`,
   `attribution`, `retrievedAt` from each doc into every chunk record's base. Index settings
   unchanged.
5. Prompts: `enrichment.enrich_batch`, `treaties._enrich_one`,
   `ebrief_monitor._generate_with_bedrock` and `scripts/enrich-metadata.py` start with
   `PROMPT_ATTRIBUTION_PREAMBLE` and a blank line, and each document block gains
   `Source URL: {url}` after `Filename`. All four only ever see Revenue material: the crawl
   enriches crawled revenue.ie URLs only (seeds are never enriched), the eBrief monitor matches
   TDM references only, and `scripts/enrich-metadata.py` gains a skip for records whose
   `category` is `PRSI (gov.ie)`.

   The eBrief monitor is zipped on its own (its directory plus `lambda/shared`) and cannot
   import the rescrape package, so it carries a local copy of what it needs: the preamble
   constant and a `_text_object_metadata(url)` helper that returns the Revenue values (the
   monitor only ever writes revenue.ie text). `tests/test_provenance.py` asserts the monitor's
   preamble equals the rescrape one and that its metadata helper returns the same dict as
   `provenance.text_object_metadata({"url": url})` for a revenue.ie URL.
6. Tests: `provenance_for` (revenue.ie URL, assets.gov.ie URL, `web.archive.org` URL with
   category `PRSI (gov.ie)`); `stamp` adds the five keys; `text_object_metadata` keys and
   ASCII, and for an archived seed record it carries the gov.ie attribution; `build_records`
   copies the five fields onto every chunk; the three prompts contain the preamble and
   `Source URL:` (assert on the string passed to the mocked client); preamble parity between
   the rescrape and eBrief copies; `scripts/enrich-metadata.py` skips a `PRSI (gov.ie)`
   record; `fetch_full_pdf_text` sends the honest `USER_AGENT` for gov.ie seeds.
7. Honest user agent for gov.ie. `corpus.SEED_USER_AGENT` (a spoofed Chrome string) and the
   `user_agent` override on `common.fetch_full_pdf_text` are removed; seed backfills send
   `IrishTaxHub-TDM-Scraper/1.0` like every other fetch. Checked 2026-09-14: assets.gov.ie's
   robots.txt allows `User-agent: *` (it blocks only named AI crawlers) and the current SW14
   seed PDF returns 200 to the honest agent. Seed text already in S3 is never refetched, so
   this only matters for a missing or too-short seed; if gov.ie then refuses the honest agent,
   `backfill_seed_text` fails closed with `RuntimeError` exactly as it does today for any seed
   fetch failure, and the run aborts before writing.
8. Docs: `README.md` Revenue Documents section and
   `docs/revenue-documents-algolia-search.md` record shape gain the five fields. `README.md`
   states how the rescrape image actually reaches ECR: the manual `tf-deploy-prod` workflow
   builds and pushes it; `tf-deploy-stage` does not; `scripts/build-rescrape.sh` is for an
   independent manual push.

Deploy: merge runs `tf-deploy-stage` (packages `ebrief_monitor`; the stage rescrape and monitor
are disabled, so nothing runs there). Dispatch `tf-deploy-prod` by hand: it builds and pushes
the rescrape image and deploys the monitor. Then let the weekly run (or a manual ECS task)
execute and confirm `revenue-docs.json` records carry `attribution` and `retrievedAt`.

### 5.5 irishtaxhubplatform (item 5)

Files: `irishtaxhubplatform/facades/ai/agent_chat.py`, new
`tests/facades/ai/test_agent_chat_prompt.py`.

1. In `AGENT_SYSTEM_PROMPT`, the "IMPORTANT - Citing sources" block applies to Revenue TDM and
   treaty documents, and its Sources example ends with the line
   `Information provided courtesy of the Revenue Commissioners under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence.`
   with the instruction "Always end the Sources section with that sentence when any Revenue
   document or treaty was used. Never describe Irish Tax Hub as official or endorsed by
   Revenue."
2. Test: `AGENT_SYSTEM_PROMPT` contains the exact statement.

Deploy: merge runs `deploy-stage`; `deploy-prod` by hand.

## 6. Sequencing

| Order | Repo | Why |
|---|---|---|
| 1 | irishtaxhub-mcp | The lawyers' question is about the plugin. Self-contained fallback, no API dependency. |
| 2 | irishtaxhub web | Public pages; independent. |
| 3 | irishtaxhubplatform | One prompt change; independent. |
| 4 | irishtaxhubapi | Makes the API self-describing; MCP adopts it automatically. |
| 5 | irishtaxhub-lambdas | Stored provenance and prompt attribution; needs the manual image build. |

Each repo gets its own branch `revenue-psi-attribution` and PR. This spec and the plan live in
`irishtaxhub-mcp/docs/plans/`.

Known rollout limitation: between step 1 and step 4 the MCP server's own fallback attributes
every text response to Revenue, including the 26 gov.ie PRSI guides, because the current API
returns no `url` or provenance for text. Step 4 closes that; the interval is days.

## 7. Out of scope

- robots.txt parsing and crawl rate limiting. Checked 2026-09-14: revenue.ie serves no
  robots.txt (its 404 page), so there is nothing to honour; assets.gov.ie allows all agents
  except named AI crawlers. A politeness delay between revenue.ie requests is a reasonable
  follow-up but not a licence matter.
- Revenue publication dates or document versions.
- Backfilling S3 metadata on existing text objects.
- Changes to what is scraped, text extraction, or Algolia index settings.
- Anthropic data-retention configuration.

## 8. Constraints

- No Revenue logo, crest or official symbol anywhere (none today; keep it so).
- Do not describe Irish Tax Hub's own tools as "official" or "authoritative" in touched copy.
- No emoji in UI copy.
- MCP `attribution.provider` stays "Irish Tax Hub"; the original publisher is recorded under
  `attribution.source`, normally Revenue and, for the PRSI guides, the Department of Social
  Protection.

## 9. Acceptance

1. A `get_revenue_document_text` call on the stage MCP endpoint returns
   `attribution.source.statement` equal to the constant, and the server's instructions
   contain it.
2. `/revenue-documents` and `/mcp` on the Vercel preview show the statement with a working
   licence link; the footer shows the multi-source statement site-wide.
3. `GET /v1/revenue/documents/text/19-07-03` on stage returns `url`, `title` and `attribution`.
4. After one rescrape run, every record in `revenue-docs.json` and `tax-treaties.json` has
   `attribution` and `retrievedAt`, gov.ie records say `Department of Social Protection
   (gov.ie)`, and a newly written `text/*.txt` object has `source-url` metadata.
5. A platform chat answer that cites a TDM ends its Sources section with the statement.
