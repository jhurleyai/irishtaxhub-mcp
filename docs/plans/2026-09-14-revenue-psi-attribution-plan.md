# Revenue PSI Licence attribution — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put Revenue's PSI Licence attribution statement on every surface that serves scraped Revenue material, and record per-document provenance where it is stored.

**Architecture:** Five independent PRs, one per repo, shipped in order: MCP server (self-contained fallback), website (static copy), platform chat (prompt), public API (attribution object on responses), scraper (provenance stamped on stored records and in enrichment prompts). The API and scraper make the MCP fallback redundant over time; nothing depends on another repo shipping first.

**Tech Stack:** Python 3.11+ (FastMCP 3.2, FastAPI, pydantic v2, pytest, black/isort/flake8), Next.js 15 + React + vitest, AWS Lambda/ECS/S3/Algolia, Terraform.

**Spec:** `docs/plans/2026-09-14-revenue-psi-attribution-spec.md` (same directory). The spec is authoritative for wording; this plan argues from it.

## Global Constraints

Exact strings. Copy, do not retype.

- `REVENUE_ATTRIBUTION_STATEMENT` = `Information provided courtesy of the Revenue Commissioners under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence`
- `PSI_MULTI_SOURCE_STATEMENT` = `Contains Irish Public Sector Information licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence`
- `REVENUE_LICENCE_URL` = `https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/public-sector-information-licence.pdf`
- `REVENUE_PSI_INFO_URL` = `https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/index.aspx`
- `CC_BY_4_URL` = `https://creativecommons.org/licenses/by/4.0/`
- `REVENUE_TDM_INDEX_URL` = `https://www.revenue.ie/en/tax-professionals/tdm/index.aspx`
- `REVENUE_TREATIES_INDEX_URL` = `https://www.revenue.ie/en/tax-professionals/tax-agreements/double-taxation-treaties/tax-treaties-by-country.aspx`
- `REVENUE_EBRIEF_INDEX_URL` = `https://www.revenue.ie/en/tax-professionals/ebrief/index.aspx`
- `MODIFICATION_NOTE` = `Irish Tax Hub has reformatted this material: document text is extracted from the original PDF or page, and descriptions, keywords and groupings are Irish Tax Hub's own. Refer to the original at source_url.`
- gov.ie provider string = `Department of Social Protection (gov.ie)`; gov.ie category string = `PRSI (gov.ie)`.
- No emoji in UI. Never call Irish Tax Hub's tools "official" or "authoritative". No Revenue logos.
- Every repo: work on branch `revenue-psi-attribution`, never commit to `main`. Run that repo's formatter, linter and tests before pushing. Each repo's CLAUDE.md gives the commands.
- Commit messages end with the Co-Authored-By and Claude-Session lines given in the session.

---

## Task 1: MCP server — attribution source block and server instructions

**Repo:** `/Users/jameshurley/projects/irishtaxhub-mcp` (branch already exists with the spec committed).

**Files:**
- Modify: `src/irishtaxhub_mcp/attribution.py`
- Modify: `src/irishtaxhub_mcp/server.py`
- Modify: `tests/test_server.py:120-139`
- Create: `tests/test_revenue_tools.py`
- Modify: `README.md`, `chatgpt-app-submission.json`, `docs/sample-questions.md`

**Interfaces:**
- Produces: `attribution.revenue_source(source_url: str) -> dict`; `_with_attribution(result, *, source_url, relevant_url=None, schema_result=False, source: Optional[dict] = None)`; `server.SERVER_INSTRUCTIONS: str`; constants named as in Global Constraints (minus the two not used here: `PSI_MULTI_SOURCE_STATEMENT`, `CC_BY_4_URL`, `REVENUE_PSI_INFO_URL`).

- [ ] **Step 1: Write the failing tests** in `tests/test_revenue_tools.py`

```python
import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx

from irishtaxhub_mcp import attribution, server

STATEMENT = (
    "Information provided courtesy of the Revenue Commissioners under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
)
LICENCE_URL = (
    "https://www.revenue.ie/en/corporate/using-revenue/"
    "reuse-of-public-sector-information/public-sector-information-licence.pdf"
)
TDM_INDEX = "https://www.revenue.ie/en/tax-professionals/tdm/index.aspx"
TREATY_INDEX = (
    "https://www.revenue.ie/en/tax-professionals/tax-agreements/"
    "double-taxation-treaties/tax-treaties-by-country.aspx"
)
EBRIEF_INDEX = "https://www.revenue.ie/en/tax-professionals/ebrief/index.aspx"

GOV_IE_ATTRIBUTION = {
    "provider": "Department of Social Protection (gov.ie)",
    "statement": (
        "Contains Irish Public Sector Information licensed under a Creative Commons "
        "Attribution 4.0 International (CC BY 4.0) licence"
    ),
    "licence": "CC BY 4.0",
    "licence_url": "https://creativecommons.org/licenses/by/4.0/",
    "source_url": "https://assets.gov.ie/x/sw14.pdf",
    "modified": True,
    "modification_note": attribution.MODIFICATION_NOTE,
}


def _client(response):
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)
    client.close = AsyncMock()
    return client


def _run(coro_fn, response, **kwargs):
    client = _client(response)
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        return asyncio.run(coro_fn(**kwargs))


def test_constants_match_spec():
    assert attribution.REVENUE_ATTRIBUTION_STATEMENT == STATEMENT
    assert attribution.REVENUE_LICENCE_URL == LICENCE_URL
    assert attribution.REVENUE_TDM_INDEX_URL == TDM_INDEX
    assert attribution.REVENUE_TREATIES_INDEX_URL == TREATY_INDEX
    assert attribution.REVENUE_EBRIEF_INDEX_URL == EBRIEF_INDEX


def test_revenue_source_shape():
    src = attribution.revenue_source("https://www.revenue.ie/x.pdf")
    assert src == {
        "provider": "Revenue Commissioners",
        "statement": STATEMENT,
        "licence": "CC BY 4.0",
        "licence_url": LICENCE_URL,
        "source_url": "https://www.revenue.ie/x.pdf",
        "modified": True,
        "modification_note": attribution.MODIFICATION_NOTE,
    }


def test_with_attribution_places_source_everywhere():
    src = attribution.revenue_source(TDM_INDEX)
    result = attribution._with_attribution(
        {"status": "success"}, source_url="https://www.irishtaxhub.ie/x", source=src
    )
    block = result.structured_content["attribution"]
    assert block["provider"] == "Irish Tax Hub"
    assert block["source"] == src
    assert block["last_updated_note"] == (
        "Date this response was generated. Source material is as last retrieved "
        "from the source identified in attribution.source."
    )
    assert json.loads(result.content[0].text)["attribution"]["source"] == src
    assert result.meta["attribution"]["source"] == src


def test_with_attribution_without_source_is_unchanged():
    result = attribution._with_attribution({"status": "success"}, source_url="https://www.irishtaxhub.ie/x")
    block = result.structured_content["attribution"]
    assert "source" not in block
    assert block["last_updated_note"] == "Live data retrieved from Irish Tax Hub on this date."


def test_upstream_attribution_is_moved_to_source():
    upstream = {"status": "success", "text": "t", "attribution": GOV_IE_ATTRIBUTION}
    result = attribution._with_attribution(
        upstream, source_url="https://www.irishtaxhub.ie/x", source=attribution.revenue_source(TDM_INDEX)
    )
    block = result.structured_content["attribution"]
    assert block["provider"] == "Irish Tax Hub"
    assert block["source"] == GOV_IE_ATTRIBUTION
    assert STATEMENT not in json.dumps(result.structured_content)


def test_get_revenue_document_text_keeps_gov_ie_upstream_attribution():
    upstream = {"status": "success", "filename": "sw14", "text": "t", "attribution": GOV_IE_ATTRIBUTION}
    result = _run(server.get_revenue_document_text, upstream, filename="sw14")
    for view in (
        result.structured_content["attribution"],
        json.loads(result.content[0].text)["attribution"],
        result.meta["attribution"],
    ):
        assert view["source"] == GOV_IE_ATTRIBUTION


def test_search_revenue_documents_source():
    result = _run(server.search_revenue_documents, {"status": "success", "results": []}, query="ppr")
    src = result.structured_content["attribution"]["source"]
    assert src["statement"] == STATEMENT
    assert src["source_url"] == TDM_INDEX


def test_list_revenue_document_categories_source():
    result = _run(server.list_revenue_document_categories, {"status": "success", "categories": []})
    assert result.structured_content["attribution"]["source"]["source_url"] == TDM_INDEX


def test_get_revenue_ebrief_changelog_source():
    result = _run(server.get_revenue_ebrief_changelog, {"status": "success", "entries": []})
    assert result.structured_content["attribution"]["source"]["source_url"] == EBRIEF_INDEX


def test_get_revenue_document_text_uses_upstream_url_or_index():
    with_url = _run(
        server.get_revenue_document_text,
        {"status": "success", "filename": "19-07-03", "text": "t", "url": "https://www.revenue.ie/a.pdf"},
        filename="19-07-03",
    )
    assert with_url.structured_content["attribution"]["source"]["source_url"] == "https://www.revenue.ie/a.pdf"
    without = _run(
        server.get_revenue_document_text,
        {"status": "success", "filename": "19-07-03", "text": "t"},
        filename="19-07-03",
    )
    assert without.structured_content["attribution"]["source"]["source_url"] == TDM_INDEX


def test_get_revenue_document_text_404_has_source():
    client = _client(None)
    response = httpx.Response(404, request=httpx.Request("GET", "http://x"))
    client.request = AsyncMock(
        side_effect=httpx.HTTPStatusError("404", request=response.request, response=response)
    )
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        result = asyncio.run(server.get_revenue_document_text(filename="missing"))
    assert result.structured_content["status"] == "error"
    assert result.structured_content["attribution"]["source"]["statement"] == STATEMENT


def test_treaty_tools_source():
    search = _run(server.search_tax_treaties, {"status": "success", "results": []}, query="dividends")
    countries = _run(server.list_tax_treaty_countries, {"status": "success", "countries": []})
    text = _run(server.get_tax_treaty_text, {"status": "success", "filename": "usa-1997", "text": "t"}, filename="usa-1997")
    for r in (search, countries, text):
        src = r.structured_content["attribution"]["source"]
        assert src["statement"] == STATEMENT
        assert src["source_url"] == TREATY_INDEX


def test_server_instructions_contain_statement():
    assert STATEMENT in server.mcp.instructions


def test_attribution_schema_declares_source():
    assert "source" in attribution._ATTRIBUTION_SCHEMA["properties"]
    assert "source" not in attribution._ATTRIBUTION_SCHEMA["required"]
    for key in ("url", "title", "displayName"):
        assert key in attribution._DOCUMENT_TEXT_OUTPUT_SCHEMA["properties"]
```

- [ ] **Step 2: Run the new tests to see them fail**

Run: `cd /Users/jameshurley/projects/irishtaxhub-mcp && poetry run pytest tests/test_revenue_tools.py -q`
Expected: failures on `AttributeError` (no `revenue_source`, no `REVENUE_ATTRIBUTION_STATEMENT`) and `TypeError` (unexpected `source` kwarg).

- [ ] **Step 3: Implement `attribution.py`**

Add after `_API_DOCS_URL` (line 21):

```python
REVENUE_ATTRIBUTION_STATEMENT = (
    "Information provided courtesy of the Revenue Commissioners under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
)
REVENUE_LICENCE_URL = (
    "https://www.revenue.ie/en/corporate/using-revenue/"
    "reuse-of-public-sector-information/public-sector-information-licence.pdf"
)
REVENUE_TDM_INDEX_URL = "https://www.revenue.ie/en/tax-professionals/tdm/index.aspx"
REVENUE_TREATIES_INDEX_URL = (
    "https://www.revenue.ie/en/tax-professionals/tax-agreements/"
    "double-taxation-treaties/tax-treaties-by-country.aspx"
)
REVENUE_EBRIEF_INDEX_URL = "https://www.revenue.ie/en/tax-professionals/ebrief/index.aspx"
MODIFICATION_NOTE = (
    "Irish Tax Hub has reformatted this material: document text is extracted from the "
    "original PDF or page, and descriptions, keywords and groupings are Irish Tax Hub's own. "
    "Refer to the original at source_url."
)
_SOURCE_NOTE = (
    "Date this response was generated. Source material is as last retrieved from the "
    "source identified in attribution.source."
)
_DEFAULT_NOTE = "Live data retrieved from Irish Tax Hub on this date."


def revenue_source(source_url: str) -> Dict[str, Any]:
    """The PSI Licence attribution object for material reused from revenue.ie."""
    return {
        "provider": "Revenue Commissioners",
        "statement": REVENUE_ATTRIBUTION_STATEMENT,
        "licence": "CC BY 4.0",
        "licence_url": REVENUE_LICENCE_URL,
        "source_url": source_url,
        "modified": True,
        "modification_note": MODIFICATION_NOTE,
    }
```

In `_ATTRIBUTION_SCHEMA["properties"]` add (not in `required`):

```python
        "source": {
            "type": "object",
            "description": "Original publisher and licence of reused public sector material.",
            "properties": {
                "provider": {"type": "string"},
                "statement": {"type": "string"},
                "licence": {"type": "string"},
                "licence_url": {"type": "string", "format": "uri"},
                "source_url": {"type": "string", "format": "uri"},
                "modified": {"type": "boolean"},
                "modification_note": {"type": "string"},
            },
            "additionalProperties": True,
        },
```

In `_DOCUMENT_TEXT_OUTPUT_SCHEMA` add `"url": {"type": "string"}, "title": {"type": "string"}, "displayName": {"type": "string"}` to the properties dict.

Replace `_with_attribution`:

```python
def _with_attribution(
    result: Any,
    *,
    source_url: str,
    relevant_url: Optional[str] = None,
    schema_result: bool = False,
    source: Optional[Dict[str, Any]] = None,
) -> ToolResult:
    """Add visible attribution without hiding or replacing the upstream result.

    ``source`` is the original publisher's attribution (see ``revenue_source``). If the
    upstream payload already carries one (the API's ``attribution`` object), that wins and
    is moved under ``attribution.source``.
    """
    continue_url = relevant_url or source_url

    if isinstance(result, dict):
        structured_content = dict(result)
    else:
        structured_content = {"result": result}

    upstream = structured_content.get("attribution")
    if isinstance(upstream, dict) and "statement" in upstream:
        source = structured_content.pop("attribution")

    attribution: Dict[str, Any] = {
        "provider": "Irish Tax Hub",
        "source_url": source_url,
        "methodology_url": _API_DOCS_URL,
        "last_updated": datetime.now(timezone.utc).date().isoformat(),
        "last_updated_note": _SOURCE_NOTE if source else _DEFAULT_NOTE,
        "relevant_url": continue_url,
        "action": {"label": "Continue on Irish Tax Hub", "url": continue_url},
    }
    if source:
        attribution["source"] = source

    attribution_key = "x-irish-tax-hub-attribution" if schema_result else "attribution"
    structured_content[attribution_key] = attribution

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(structured_content, ensure_ascii=False, default=str),
            ),
            ResourceLink(
                type="resource_link",
                name="continue-on-irish-tax-hub",
                title="Continue on Irish Tax Hub",
                uri=continue_url,
                description="Open the relevant Irish Tax Hub calculator or guide.",
                mimeType="text/html",
            ),
        ],
        structured_content=structured_content,
        meta={"attribution": attribution},
    )
```

- [ ] **Step 4: Implement `server.py`**

Extend the `from .attribution import (...)` block with `REVENUE_EBRIEF_INDEX_URL, REVENUE_TDM_INDEX_URL, REVENUE_TREATIES_INDEX_URL, revenue_source`. Replace `mcp = FastMCP("irishtaxhub-mcp")` with:

```python
SERVER_INSTRUCTIONS = (
    "Irish Tax Hub tools return Irish tax calculations and reference material. The Revenue "
    "document, eBrief and tax-treaty tools return material published by the Office of the "
    "Revenue Commissioners (revenue.ie) and reused under Revenue's Public Sector Information "
    "Licence (CC BY 4.0). When your answer relies on that material: include the statement "
    '"Information provided courtesy of the Revenue Commissioners under a Creative Commons '
    'Attribution 4.0 International (CC BY 4.0) licence"; link to the original document using '
    "the result's `url` field or `attribution.source.source_url`; and note that document text "
    "is extracted from the original and that descriptions and keywords are Irish Tax Hub's own. "
    'A few records come from gov.ie rather than Revenue (category "PRSI (gov.ie)"); where a '
    "result carries its own `attribution` and `licenceUrl` fields, reproduce those instead. "
    "Do not present Irish Tax Hub or its tools as official or endorsed by Revenue."
)

mcp = FastMCP("irishtaxhub-mcp", instructions=SERVER_INSTRUCTIONS)
```

In each of the seven tools add `source=` to the `_with_attribution` call:

| Tool | `source=` |
|---|---|
| `search_revenue_documents`, `list_revenue_document_categories` | `revenue_source(REVENUE_TDM_INDEX_URL)` |
| `get_revenue_ebrief_changelog` | `revenue_source(REVENUE_EBRIEF_INDEX_URL)` |
| `get_revenue_document_text` success | `revenue_source(result.get("url") or REVENUE_TDM_INDEX_URL)` (guard `isinstance(result, dict)`) |
| `get_revenue_document_text` 404 | `revenue_source(REVENUE_TDM_INDEX_URL)` |
| `search_tax_treaties`, `list_tax_treaty_countries` | `revenue_source(REVENUE_TREATIES_INDEX_URL)` |
| `get_tax_treaty_text` success / 404 | `revenue_source(result.get("url") or REVENUE_TREATIES_INDEX_URL)` / `revenue_source(REVENUE_TREATIES_INDEX_URL)` |

Append to each of the seven docstrings, as the last paragraph:

```
    Content is reused from public sector sources, normally revenue.ie under Revenue's PSI
    Licence (CC BY 4.0); reproduce the result's own attribution where present, otherwise
    attribution.source.statement, when citing.
```

- [ ] **Step 5: Update the existing shape test** `tests/test_server.py:120-139`: add `assert "source" not in attribution` after the `action` assertion.

- [ ] **Step 6: Run the full suite, formatter and linter**

Run: `poetry run pytest -q && poetry run black --check . && poetry run isort --check-only . && poetry run flake8 .`
Expected: all pass (run `poetry run black . && poetry run isort .` first if formatting differs).

- [ ] **Step 7: Docs and manifest**

`README.md`: after the Tools table insert

```markdown
## Source material and licensing

The Revenue document, eBrief and tax-treaty tools return material published by the Office of
the Revenue Commissioners and reused under Revenue's [Public Sector Information Licence](https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/public-sector-information-licence.pdf)
(CC BY 4.0):

> Information provided courtesy of the Revenue Commissioners under a Creative Commons
> Attribution 4.0 International (CC BY 4.0) licence

Every such result carries this statement in `attribution.source`. Document text is extracted
from Revenue's original PDFs; descriptions, keywords and groupings are Irish Tax Hub's own.
Irish Tax Hub is not affiliated with or endorsed by Revenue.
```

`chatgpt-app-submission.json`: append ` Content is reused under Revenue's PSI Licence (CC BY 4.0) with attribution in every response.` to the seven `read_only_justification` strings (lines 54, 62, 70, 78, 86, 94, 102) and ` and Revenue PSI Licence attribution` to the `expected_output` of the two document test cases (search_revenue_documents, search_tax_treaties). Edit with a text editor, not black (see memory: black corrupts JSON). Validate: `python3 -m json.tool chatgpt-app-submission.json > /dev/null`.

`docs/sample-questions.md`: delete the `## AI Summary` section (lines 124-132); add under `## Revenue Documents`: `Results carry Revenue's PSI Licence attribution in attribution.source; reproduce it when citing.`

- [ ] **Step 8: Commit**

```bash
git add -A src tests README.md chatgpt-app-submission.json docs/sample-questions.md
git commit -m "feat: Revenue PSI Licence attribution on document, eBrief and treaty tools"
```

Do not stage `submission-assets/openai-directory-icon.png` (pre-existing unrelated change).

---

## Task 2: Website — attribution component, pages and footer

**Repo:** `/Users/jameshurley/projects/irishtaxhub`, workspace `apps/web`.

**Files:**
- Create: `apps/web/src/components/RevenueAttribution.tsx`, `apps/web/src/components/RevenueAttribution.test.tsx`
- Modify: `apps/web/src/app/(marketing)/revenue-documents/RevenueDocumentsSearch.tsx:151-157`
- Modify: `apps/web/src/app/(marketing)/mcp/page.tsx:11-12, 84-91, ~200`
- Modify: `apps/web/src/components/Footer.tsx:550-554`

- [ ] **Step 1: Write the failing test** `RevenueAttribution.test.tsx`

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RevenueAttribution } from "./RevenueAttribution";

const LICENCE =
    "https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/public-sector-information-licence.pdf";
const INFO =
    "https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/index.aspx";

describe("RevenueAttribution", () => {
    it("renders the statement with licence links in full mode", () => {
        render(<RevenueAttribution variant="full" />);
        expect(
            screen.getByText(/Information provided courtesy of the Revenue Commissioners/),
        ).toBeTruthy();
        const licence = screen.getByRole("link", {
            name: /Creative Commons Attribution 4\.0 International \(CC BY 4\.0\) licence/,
        });
        expect(licence.getAttribute("href")).toBe(LICENCE);
        expect(licence.getAttribute("rel")).toBe("noopener noreferrer");
        expect(
            screen.getByRole("link", { name: "About Revenue's re-use policy" }).getAttribute("href"),
        ).toBe(INFO);
        expect(screen.getByText(/not affiliated with or endorsed by Revenue/)).toBeTruthy();
    });

    it("omits the second sentence in compact mode", () => {
        render(<RevenueAttribution variant="compact" />);
        expect(screen.queryByText(/not affiliated/)).toBeNull();
    });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd /Users/jameshurley/projects/irishtaxhub/apps/web && npx vitest run src/components/RevenueAttribution.test.tsx`
Expected: fails, module not found.

- [ ] **Step 3: Implement the component**

```tsx
export const REVENUE_LICENCE_URL =
    "https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/public-sector-information-licence.pdf";
export const REVENUE_PSI_INFO_URL =
    "https://www.revenue.ie/en/corporate/using-revenue/reuse-of-public-sector-information/index.aspx";
export const CC_BY_4_URL = "https://creativecommons.org/licenses/by/4.0/";

type Props = { variant: "full" | "compact"; className?: string };

export function RevenueAttribution({ variant, className = "" }: Props) {
    return (
        <div className={`text-sm text-base-content/70 space-y-1 ${className}`}>
            <p>
                Information provided courtesy of the Revenue Commissioners under a{" "}
                <a
                    href={REVENUE_LICENCE_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="link"
                >
                    Creative Commons Attribution 4.0 International (CC BY 4.0) licence
                </a>
                .{" "}
                <a
                    href={REVENUE_PSI_INFO_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="link"
                >
                    About Revenue&apos;s re-use policy
                </a>
            </p>
            {variant === "full" && (
                <p>
                    Document text is extracted from the original PDFs and may differ in
                    layout; descriptions and keywords are written by Irish Tax Hub. PRSI
                    guides are published by the Department of Social Protection on gov.ie
                    under CC BY 4.0. Always check the original document. Irish Tax Hub is
                    not affiliated with or endorsed by Revenue.
                </p>
            )}
        </div>
    );
}
```

- [ ] **Step 4: Run the test to see it pass.** Same command as Step 2. Expected: 2 passed.

- [ ] **Step 5: Wire it into the pages**

`RevenueDocumentsSearch.tsx`: import `{ RevenueAttribution } from "@/components/RevenueAttribution";` and after the intro `<p>` (ends line 157) insert `<RevenueAttribution variant="full" className="mt-3" />`.

`mcp/page.tsx`:
- add `import { RevenueAttribution } from "@/components/RevenueAttribution";` with the other imports.
- line 12 `description`: `"Connect Claude to Irish tax tools and reference material — calculators, Revenue Tax & Duty Manuals, tax constants and key dates, and Ireland's double-taxation treaties."`
- hero paragraph (84-91) text becomes the spec 5.2 item 3 wording (starts "Connect Claude directly to Irish tax tools and reference material.").
- after the "Data and privacy" section add:

```tsx
            <section className="px-6 py-12">
                <div className="container mx-auto max-w-4xl">
                    <Heading as="h2" size="md" className="mb-6">
                        Source material and licensing
                    </Heading>
                    <RevenueAttribution variant="full" />
                    <p className="mt-4 text-base-content/70">
                        Every Revenue-derived tool result carries this attribution in its
                        attribution.source field.
                    </p>
                </div>
            </section>
```

`Footer.tsx`: before the `{/* Copyright */}` paragraph insert

```tsx
                    <p className="text-center text-on-ink/60 text-sm">
                        Contains Irish Public Sector Information licensed under a Creative
                        Commons Attribution 4.0 International (
                        <a
                            href={CC_BY_4_URL}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline"
                        >
                            CC BY 4.0
                        </a>
                        ) licence.
                    </p>
```

with `import { CC_BY_4_URL } from "./RevenueAttribution";`.

- [ ] **Step 6: Lint, format, test, build**

Run from `apps/web`: `npm run lint && npm run format && npx vitest run && npm run build` (the repo's hooks format on save; run `npm run format` inside the workspace, per memory).
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git checkout -b revenue-psi-attribution
git add apps/web/src/components/RevenueAttribution.tsx apps/web/src/components/RevenueAttribution.test.tsx "apps/web/src/app/(marketing)/revenue-documents/RevenueDocumentsSearch.tsx" "apps/web/src/app/(marketing)/mcp/page.tsx" apps/web/src/components/Footer.tsx
git commit -m "feat(web): Revenue PSI Licence attribution on documents page, MCP page and footer"
```

---

## Task 3: Platform chat — attribution in the Sources instruction

**Repo:** `/Users/jameshurley/projects/irishtaxhubplatform`.

**Files:**
- Modify: `irishtaxhubplatform/facades/ai/agent_chat.py:96-106`
- Create: `tests/facades/ai/test_agent_chat_prompt.py`

- [ ] **Step 1: Write the failing test**

```python
from irishtaxhubplatform.facades.ai.agent_chat import AGENT_SYSTEM_PROMPT

STATEMENT = (
    "Information provided courtesy of the Revenue Commissioners under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence."
)


def test_system_prompt_requires_revenue_attribution():
    assert STATEMENT in AGENT_SYSTEM_PROMPT
    assert "Sources" in AGENT_SYSTEM_PROMPT
```

- [ ] **Step 2: Run it to see it fail.** `poetry run pytest tests/facades/ai/test_agent_chat_prompt.py -q`. Expected: assertion fails on the statement.

- [ ] **Step 3: Edit the prompt.** Replace the "IMPORTANT - Citing sources" block with:

```
IMPORTANT - Citing sources:
When you use Revenue TDM documents or tax-treaty documents in your answer, you MUST
include a "Sources" section at the bottom of your response listing each document
you referenced. Format each source as a markdown link using the `url` field from
the search results, and end the section with Revenue's licence attribution:

Sources:
- [Document Title](https://www.revenue.ie/tdm/path/to/document.pdf)
- [Document Title](https://www.revenue.ie/tdm/path/to/document.pdf)

Information provided courtesy of the Revenue Commissioners under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence.

Always end the Sources section with that sentence when any Revenue document or
treaty was used. Never describe Irish Tax Hub as official or endorsed by Revenue.
```

- [ ] **Step 4: Run tests, format, lint.** `poetry run pytest -q && poetry run black --check . && poetry run isort --check-only . && poetry run flake8`. Expected: pass.

- [ ] **Step 5: Commit** on `revenue-psi-attribution`: `git commit -m "feat(ai): require Revenue PSI Licence attribution in chat Sources"`.

---

## Task 4: Public API — attribution object on Revenue and treaty responses

**Repo:** `/Users/jameshurley/projects/irishtaxhubapi`.

**Files:**
- Create: `irishtaxhubapi/schemas/attribution.py`
- Modify: `irishtaxhubapi/schemas/revenue_docs.py`, `irishtaxhubapi/schemas/tax_treaties.py`
- Modify: `irishtaxhubapi/facades/revenue_docs/facade.py` (add `get_document`), `irishtaxhubapi/facades/tax_treaties/facade.py` (add `get_treaty`)
- Modify: `irishtaxhubapi/routers/v1.py:1403-1540`
- Create: `tests/views/test_revenue_docs_routes.py`
- Modify: `tests/views/test_tax_treaties_routes.py`, `tests/facades/test_revenue_docs.py`, `tests/facades/test_tax_treaties.py`

**Interfaces:**
- Produces: `RevenueAttribution` model; `revenue_attribution(source_url) -> RevenueAttribution`; `attribution_for(record) -> RevenueAttribution`; `RevenueDocsFacade.get_document(filename) -> Optional[dict]`; `TaxTreatiesFacade.get_treaty(filename) -> Optional[dict]`.

- [ ] **Step 1: Write failing route tests** `tests/views/test_revenue_docs_routes.py`

```python
from unittest.mock import patch

from fastapi.testclient import TestClient

from irishtaxhubapi.app import create_app
from irishtaxhubapi.schemas.attribution import (
    CC_BY_4_URL,
    PSI_MULTI_SOURCE_STATEMENT,
    REVENUE_ATTRIBUTION_STATEMENT,
    REVENUE_EBRIEF_INDEX_URL,
    REVENUE_TDM_INDEX_URL,
)

client = TestClient(create_app())
FACADE = "irishtaxhubapi.facades.revenue_docs.facade.RevenueDocsFacade"

SAMPLE = [
    {
        "url": "https://www.revenue.ie/en/tax-professionals/tdm/x/part-19/19-07-03.pdf",
        "title": "19 07 03",
        "displayName": "PPR Relief",
        "description": "d",
        "keywords": ["ppr"],
        "category": "Income Tax",
        "subcategory": "Part 19",
    },
    {
        "url": "https://web.archive.org/web/2020/https://assets.gov.ie/x/sw14-2020.pdf",
        "title": "SW 14 2020",
        "displayName": "PRSI 2020",
        "description": "d",
        "keywords": ["prsi"],
        "category": "PRSI (gov.ie)",
        "subcategory": "2020",
    },
]


def test_search_has_revenue_attribution():
    with patch(f"{FACADE}._load_docs", return_value=SAMPLE), patch(
        "irishtaxhubapi.facades.revenue_docs.facade.ALGOLIA_SEARCH_KEY", ""
    ):
        r = client.get("/v1/revenue/documents", params={"q": "ppr"})
    assert r.status_code == 200
    body = r.json()
    assert body["attribution"]["statement"] == REVENUE_ATTRIBUTION_STATEMENT
    assert body["attribution"]["source_url"] == REVENUE_TDM_INDEX_URL
    assert body["source"] == "s3"


def test_categories_and_changelog_have_attribution():
    with patch(f"{FACADE}._load_docs", return_value=SAMPLE), patch(
        f"{FACADE}._load_changelog", return_value={"entries": [], "last_checked": ""}
    ):
        cats = client.get("/v1/revenue/documents/categories").json()
        log = client.get("/v1/revenue/documents/changelog").json()
    assert cats["attribution"]["source_url"] == REVENUE_TDM_INDEX_URL
    assert log["attribution"]["source_url"] == REVENUE_EBRIEF_INDEX_URL


def test_text_has_document_url_and_attribution():
    with patch(f"{FACADE}._load_docs", return_value=SAMPLE), patch(
        f"{FACADE}.get_document_text", return_value="body"
    ):
        r = client.get("/v1/revenue/documents/text/19-07-03")
    body = r.json()
    assert body["url"] == SAMPLE[0]["url"]
    assert body["title"] == "19 07 03"
    assert body["displayName"] == "PPR Relief"
    assert body["attribution"]["source_url"] == SAMPLE[0]["url"]
    assert body["attribution"]["statement"] == REVENUE_ATTRIBUTION_STATEMENT


def test_text_for_gov_ie_record_uses_gov_ie_attribution():
    with patch(f"{FACADE}._load_docs", return_value=SAMPLE), patch(
        f"{FACADE}.get_document_text", return_value="body"
    ):
        body = client.get("/v1/revenue/documents/text/sw14-2020").json()
    assert body["attribution"]["provider"] == "Department of Social Protection (gov.ie)"
    assert body["attribution"]["statement"] == PSI_MULTI_SOURCE_STATEMENT
    assert body["attribution"]["licence_url"] == CC_BY_4_URL


def test_text_stored_provenance_wins():
    stored = dict(SAMPLE[1], sourceOrganisation="DSP", attribution="stored", licenceUrl="https://l")
    with patch(f"{FACADE}._load_docs", return_value=[stored]), patch(
        f"{FACADE}.get_document_text", return_value="body"
    ):
        body = client.get("/v1/revenue/documents/text/sw14-2020").json()
    assert body["attribution"]["provider"] == "DSP"
    assert body["attribution"]["statement"] == "stored"
    assert body["attribution"]["licence_url"] == "https://l"


def test_text_unknown_record_falls_back_to_index():
    with patch(f"{FACADE}._load_docs", return_value=SAMPLE), patch(
        f"{FACADE}.get_document_text", return_value="body"
    ):
        body = client.get("/v1/revenue/documents/text/unknown").json()
    assert body["url"] == ""
    assert body["attribution"]["source_url"] == REVENUE_TDM_INDEX_URL


def test_text_404_unchanged():
    with patch(f"{FACADE}.get_document_text", return_value=None), patch(
        f"{FACADE}._load_docs", return_value=SAMPLE
    ):
        r = client.get("/v1/revenue/documents/text/missing")
    assert r.status_code == 404
    assert r.json() == {"status": "error", "message": "Text not found for missing"}
```

Add to `tests/views/test_tax_treaties_routes.py`:

```python
from irishtaxhubapi.schemas.attribution import REVENUE_ATTRIBUTION_STATEMENT, REVENUE_TREATIES_INDEX_URL


def test_treaty_endpoints_have_attribution():
    facade = "irishtaxhubapi.facades.tax_treaties.facade.TaxTreatiesFacade"
    with patch(f"{facade}._load_docs", return_value=SAMPLE), patch(
        f"{facade}.get_treaty_text", return_value="body"
    ):
        search = client.get("/v1/tax-treaties", params={"country": "France"}).json()
        countries = client.get("/v1/tax-treaties/countries").json()
        text = client.get("/v1/tax-treaties/text/france").json()
    assert search["attribution"]["source_url"] == REVENUE_TREATIES_INDEX_URL
    assert countries["attribution"]["statement"] == REVENUE_ATTRIBUTION_STATEMENT
    assert text["url"] == "https://x/f/france.pdf"
    assert text["attribution"]["source_url"] == "https://x/f/france.pdf"
```

Facade tests, appended to `tests/facades/test_revenue_docs.py` (uses the existing `facade` fixture and `SAMPLE_DOCS`):

```python
class TestGetDocument:
    def test_found_by_stem(self, facade):
        assert facade.get_document("15-01-10")["displayName"] == "Principal Private Residence Relief"

    def test_pdf_suffix_case_insensitive(self, facade):
        assert facade.get_document("15-01-10.PDF")["displayName"] == "Principal Private Residence Relief"

    def test_full_url_and_query(self, facade):
        assert facade.get_document("https://www.revenue.ie/tdm/income-tax/15-01-10.pdf?x=1")["subcategory"] == "Part 15"

    def test_not_found(self, facade):
        assert facade.get_document("nope") is None
```

Add a Notes-for-Guidance doc to `SAMPLE_DOCS` if `_text_url_for` produces a compound stem for it (check `facade.py:271-288` for the rule) and assert `get_document(<that stem>)` finds it. Mirror a `TestGetTreaty` class in `tests/facades/test_tax_treaties.py` with `get_treaty("usa-1997")`, `("USA-1997.pdf")` is `None` (stems are case-sensitive; only the extension is case-insensitive), and `("missing")`.

- [ ] **Step 2: Run to see failures.** `poetry run pytest tests/views/test_revenue_docs_routes.py tests/views/test_tax_treaties_routes.py tests/facades -q`. Expected: ImportError on `schemas.attribution`.

- [ ] **Step 3: Create `schemas/attribution.py`**

```python
"""Public Sector Information Licence attribution for reused public sector material."""

from urllib.parse import urlparse

from pydantic import BaseModel

REVENUE_ATTRIBUTION_STATEMENT = (
    "Information provided courtesy of the Revenue Commissioners under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
)
PSI_MULTI_SOURCE_STATEMENT = (
    "Contains Irish Public Sector Information licensed under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
)
REVENUE_LICENCE_URL = (
    "https://www.revenue.ie/en/corporate/using-revenue/"
    "reuse-of-public-sector-information/public-sector-information-licence.pdf"
)
CC_BY_4_URL = "https://creativecommons.org/licenses/by/4.0/"
REVENUE_TDM_INDEX_URL = "https://www.revenue.ie/en/tax-professionals/tdm/index.aspx"
REVENUE_TREATIES_INDEX_URL = (
    "https://www.revenue.ie/en/tax-professionals/tax-agreements/"
    "double-taxation-treaties/tax-treaties-by-country.aspx"
)
REVENUE_EBRIEF_INDEX_URL = "https://www.revenue.ie/en/tax-professionals/ebrief/index.aspx"
MODIFICATION_NOTE = (
    "Irish Tax Hub has reformatted this material: document text is extracted from the "
    "original PDF or page, and descriptions, keywords and groupings are Irish Tax Hub's own. "
    "Refer to the original at source_url."
)
GOV_IE_PROVIDER = "Department of Social Protection (gov.ie)"
GOV_IE_CATEGORY = "PRSI (gov.ie)"


class RevenueAttribution(BaseModel):
    provider: str
    statement: str
    licence: str = "CC BY 4.0"
    licence_url: str
    source_url: str
    modified: bool = True
    modification_note: str = MODIFICATION_NOTE


def revenue_attribution(source_url: str) -> RevenueAttribution:
    return RevenueAttribution(
        provider="Revenue Commissioners",
        statement=REVENUE_ATTRIBUTION_STATEMENT,
        licence_url=REVENUE_LICENCE_URL,
        source_url=source_url,
    )


def _is_gov_ie(record: dict) -> bool:
    if record.get("category") == GOV_IE_CATEGORY:
        return True
    host = urlparse(record.get("url", "")).hostname or ""
    return host == "gov.ie" or host.endswith(".gov.ie")


def attribution_for(record: dict) -> RevenueAttribution:
    """Attribution for one corpus record. Stored provenance (from the scraper) wins."""
    url = record.get("url", "")
    if _is_gov_ie(record):
        base = RevenueAttribution(
            provider=GOV_IE_PROVIDER,
            statement=PSI_MULTI_SOURCE_STATEMENT,
            licence_url=CC_BY_4_URL,
            source_url=url,
        )
    else:
        base = revenue_attribution(url)
    if record.get("sourceOrganisation") and record.get("attribution") and record.get("licenceUrl"):
        return base.model_copy(
            update={
                "provider": record["sourceOrganisation"],
                "statement": record["attribution"],
                "licence_url": record["licenceUrl"],
            }
        )
    return base
```

- [ ] **Step 4: Schemas.** In `schemas/revenue_docs.py` import `RevenueAttribution` and add `attribution: RevenueAttribution` to `RevenueDocsSearchResponse`, `RevenueCategoryResponse`, `EbriefChangelogResponse`, `RevenueDocumentTextResponse`; add `url: str = ""`, `title: str = ""`, `displayName: str = Field(default="", alias="displayName")` with `model_config = {"populate_by_name": True}` to `RevenueDocumentTextResponse`; add `sourceOrganisation: str = Field(default="", alias="sourceOrganisation")`, `attribution: str = ""`, `licenceUrl: str = Field(default="", alias="licenceUrl")` to `RevenueDocument`. Same for `schemas/tax_treaties.py` (`TaxTreaty`, `TaxTreatySearchResponse`, `TaxTreatyCountryResponse`, `TaxTreatyTextResponse`).

- [ ] **Step 5: Facades.** Add to `RevenueDocsFacade`:

```python
    @staticmethod
    def _normalise_identifier(value: str) -> str:
        stem = value.strip().split("?", 1)[0].split("#", 1)[0].rstrip("/").split("/")[-1]
        return re.sub(r"\.pdf$", "", stem, flags=re.IGNORECASE)

    def get_document(self, filename: str) -> Optional[dict]:
        """Corpus record whose text identifier matches ``filename`` (URL, path or stem)."""
        wanted = self._normalise_identifier(filename)
        for doc in self._load_docs():
            if self._text_url_for(doc.get("url", "")).rsplit("/", 1)[-1] == wanted:
                return doc
        return None
```

Add the same pair to `TaxTreatiesFacade` named `get_treaty`.

Both `_search_algolia` methods build each result dict by hand (`revenue_docs/facade.py:154-166`, `tax_treaties/facade.py:109-122`), so the provenance fields stored by Task 5 would be dropped on the Algolia path. In both, after the dict is built add:

```python
            for field in ("sourceOrganisation", "licence", "licenceUrl", "attribution", "retrievedAt"):
                if hit.get(field):
                    doc[field] = hit[field]
```

and add an Algolia-path facade test: patch `urllib.request.urlopen` (see the existing Algolia tests in `tests/facades/test_revenue_docs.py` for the pattern; if none exist, patch `RevenueDocsFacade._search_algolia` is not enough, so mock `urlopen` to return `{"hits": [{"docUrl": "u", "attribution": "A", "licenceUrl": "L", "sourceOrganisation": "S"}], "nbHits": 1}`) and assert the three values survive in `search(query="x")["results"][0]` with `ALGOLIA_SEARCH_KEY` patched to a non-empty string.

- [ ] **Step 6: Routers.** Import `attribution_for, revenue_attribution, REVENUE_EBRIEF_INDEX_URL, REVENUE_TDM_INDEX_URL, REVENUE_TREATIES_INDEX_URL` from `..schemas.attribution`. In each of the seven routes add `"attribution": ...` to the returned dict per spec 5.3 item 4. Revenue text route body becomes:

```python
    facade = RevenueDocsFacade()
    text = facade.get_document_text(filename)
    if text is None:
        return JSONResponse(
            {"status": "error", "message": f"Text not found for {filename}"},
            status_code=404,
        )
    record = facade.get_document(filename)
    if record is None:
        return {
            "status": "success",
            "filename": filename,
            "text": text,
            "attribution": revenue_attribution(REVENUE_TDM_INDEX_URL),
        }
    return {
        "status": "success",
        "filename": filename,
        "text": text,
        "url": record.get("url", ""),
        "title": record.get("title", ""),
        "displayName": record.get("displayName", ""),
        "attribution": attribution_for(record),
    }
```

Treaty text mirrors it with `get_treaty` and `REVENUE_TREATIES_INDEX_URL`. Append the spec 5.3 item 5 sentence to each route's `description`.

- [ ] **Step 7: Run everything.** `poetry run pytest -q && poetry run black --check . && poetry run isort --check-only . && poetry run flake8`. Expected: pass. If `tests/test_schema_exports.py` enumerates schema modules, add the new module to it.

- [ ] **Step 8: Commit** on `revenue-psi-attribution`: `git commit -m "feat(api): PSI Licence attribution object on Revenue document and treaty responses"`.

---

## Task 5: Scraper — provenance on stored records, prompts and text objects

**Repo:** `/Users/jameshurley/projects/irishtaxhub-lambdas`.

**Files:**
- Create: `lambda/revenue_docs/rescrape/provenance.py`, `tests/test_provenance.py`
- Modify: `lambda/revenue_docs/rescrape/Dockerfile:11` (add `provenance.py` to `COPY`)
- Modify: `rescrape/corpus.py` (`_save_seed_text_strict`, `backfill_seed_text`, `save_text`, `save_docs`, remove `SEED_USER_AGENT`), `rescrape/common.py:54-61` (remove `user_agent` param), `rescrape/app.py` (`main`, `_enrich_new_docs`), `rescrape/enrichment.py:90-122`, `rescrape/treaties.py` (`_enrich_one`, `save_treaty_text`, `run`), `rescrape/algolia_index.py:197-240`
- Modify: `lambda/revenue_docs/ebrief_monitor/app.py` (`save_text_to_s3`, `_generate_with_bedrock`)
- Modify: `scripts/enrich-metadata.py` (preamble, `Source URL`, skip gov.ie)
- Modify tests: `tests/test_prsi_seed.py` (the `SEED_USER_AGENT` assertion), `tests/test_rescrape_crawl.py`, `tests/test_treaties.py`, `tests/test_ebrief_monitor.py`, `tests/test_algolia_index.py`
- Modify docs: `README.md`, `docs/revenue-documents-algolia-search.md`

**Interfaces:**
- Produces: `provenance.provenance_for(record) -> dict`; `provenance.stamp(records, retrieved_at) -> list[dict]`; `provenance.text_object_metadata(record) -> dict`; `provenance.PROMPT_ATTRIBUTION_PREAMBLE`; `provenance.REVENUE_PROVENANCE`, `provenance.GOV_IE_PROVENANCE`; ebrief monitor `PROMPT_ATTRIBUTION_PREAMBLE` and `_text_object_metadata(url)`.

- [ ] **Step 1: Write failing tests** `tests/test_provenance.py`

```python
import importlib.util
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lambda", "revenue_docs", "rescrape"))

import provenance  # noqa: E402

STATEMENT = (
    "Information provided courtesy of the Revenue Commissioners under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
)
REVENUE_URL = "https://www.revenue.ie/en/tax-professionals/tdm/x/19-07-03.pdf"
GOV_URL = "https://assets.gov.ie/static/documents/sw14.pdf"
ARCHIVED = {"url": "https://web.archive.org/web/2020/https://assets.gov.ie/x.pdf", "category": "PRSI (gov.ie)"}


def _load(path_parts):
    path = os.path.join(os.path.dirname(__file__), "..", *path_parts)
    spec = importlib.util.spec_from_file_location(path_parts[-1].replace(".py", "_mod"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_constants():
    assert provenance.REVENUE_ATTRIBUTION_STATEMENT == STATEMENT
    assert provenance.REVENUE_PROVENANCE["attribution"] == STATEMENT
    assert provenance.GOV_IE_PROVENANCE["sourceOrganisation"] == "Department of Social Protection (gov.ie)"


def test_provenance_for():
    assert provenance.provenance_for({"url": REVENUE_URL}) is provenance.REVENUE_PROVENANCE
    assert provenance.provenance_for({"url": GOV_URL}) is provenance.GOV_IE_PROVENANCE
    assert provenance.provenance_for(ARCHIVED) is provenance.GOV_IE_PROVENANCE
    assert provenance.provenance_for({"url": "https://www.gov.ie/x.pdf"}) is provenance.GOV_IE_PROVENANCE


def test_stamp_adds_five_keys_without_mutating():
    original = {"url": REVENUE_URL, "title": "t"}
    out = provenance.stamp([original], "2026-09-14T03:00:00+00:00")
    assert "attribution" not in original
    assert out[0]["sourceOrganisation"] == "Revenue Commissioners"
    assert out[0]["licence"] == "CC BY 4.0"
    assert out[0]["licenceUrl"] == provenance.REVENUE_LICENCE_URL
    assert out[0]["attribution"] == STATEMENT
    assert out[0]["retrievedAt"] == "2026-09-14T03:00:00+00:00"


def test_text_object_metadata():
    meta = provenance.text_object_metadata({"url": REVENUE_URL})
    assert set(meta) == {"source-url", "licence", "licence-url", "attribution"}
    assert all(v.isascii() for v in meta.values())
    assert provenance.text_object_metadata(ARCHIVED)["attribution"] == provenance.GOV_IE_PROVENANCE["attribution"]


def test_ebrief_monitor_copies_match():
    saved = sys.modules.pop("sentry_init", None)
    import types
    from unittest.mock import MagicMock

    stub = types.ModuleType("sentry_init")
    stub.sentry_handler = lambda fn: fn
    sys.modules["sentry_init"] = stub
    sys.modules.setdefault("boto3", MagicMock())
    try:
        monitor = _load(["lambda", "revenue_docs", "ebrief_monitor", "app.py"])
    finally:
        if saved is not None:
            sys.modules["sentry_init"] = saved
    assert monitor.PROMPT_ATTRIBUTION_PREAMBLE == provenance.PROMPT_ATTRIBUTION_PREAMBLE
    assert monitor._text_object_metadata(REVENUE_URL) == provenance.text_object_metadata({"url": REVENUE_URL})
```

Also add, in the existing test files:
- `tests/test_rescrape_crawl.py`: a test that `enrichment.enrich_batch([(REVENUE_URL, "text")], client)` sends a prompt starting with the preamble and containing `Source URL: {REVENUE_URL}` (mock `client.messages.create` to return `content=[SimpleNamespace(text="{}")]`).
- `tests/test_treaties.py`: same for `treaties._enrich_one`.
- `tests/test_ebrief_monitor.py`: same for `_generate_with_bedrock` with `boto3.client` mocked; and `save_text_to_s3` passes `Metadata` with `source-url`.
- `tests/test_algolia_index.py`: `build_records([{**doc, "sourceOrganisation": "R", "licence": "L", "licenceUrl": "U", "attribution": "A", "retrievedAt": "T"}], load_text=lambda u: "x")` yields records each carrying those five values.
- `tests/test_prsi_seed.py:~325`: change `assert seen["ua"] == app.SEED_USER_AGENT` to `assert seen["ua"] == common.USER_AGENT` (import `common`), and adjust the `_capture` helper if it inspected `user_agent`.
- a script test: load `scripts/enrich-metadata.py` by path and assert its `enrich_batch` prompt starts with the preamble and that a helper `should_enrich(doc)` returns `False` for `{"category": "PRSI (gov.ie)"}`.

- [ ] **Step 2: Run to see failures.** `pytest tests/test_provenance.py -q`. Expected: ModuleNotFoundError `provenance`.

- [ ] **Step 3: Create `provenance.py`**

```python
"""Licence provenance for reused public sector material (Revenue PSI Licence, gov.ie CC BY)."""

from urllib.parse import urlparse

REVENUE_ATTRIBUTION_STATEMENT = (
    "Information provided courtesy of the Revenue Commissioners under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
)
PSI_MULTI_SOURCE_STATEMENT = (
    "Contains Irish Public Sector Information licensed under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
)
REVENUE_LICENCE_URL = (
    "https://www.revenue.ie/en/corporate/using-revenue/"
    "reuse-of-public-sector-information/public-sector-information-licence.pdf"
)
CC_BY_4_URL = "https://creativecommons.org/licenses/by/4.0/"
GOV_IE_CATEGORY = "PRSI (gov.ie)"

PROMPT_ATTRIBUTION_PREAMBLE = (
    "The excerpts below are extracts from documents published by the Office of the Revenue "
    "Commissioners (revenue.ie), reused under Revenue's Public Sector Information Licence "
    '(CC BY 4.0). Attribution: "' + REVENUE_ATTRIBUTION_STATEMENT + '". Licence: '
    + REVENUE_LICENCE_URL
)

REVENUE_PROVENANCE = {
    "sourceOrganisation": "Revenue Commissioners",
    "licence": "CC BY 4.0",
    "licenceUrl": REVENUE_LICENCE_URL,
    "attribution": REVENUE_ATTRIBUTION_STATEMENT,
}
GOV_IE_PROVENANCE = {
    "sourceOrganisation": "Department of Social Protection (gov.ie)",
    "licence": "CC BY 4.0",
    "licenceUrl": CC_BY_4_URL,
    "attribution": PSI_MULTI_SOURCE_STATEMENT,
}


def provenance_for(record):
    if record.get("category") == GOV_IE_CATEGORY:
        return GOV_IE_PROVENANCE
    host = urlparse(record.get("url", "")).hostname or ""
    if host == "gov.ie" or host.endswith(".gov.ie"):
        return GOV_IE_PROVENANCE
    return REVENUE_PROVENANCE


def stamp(records, retrieved_at):
    return [{**r, **provenance_for(r), "retrievedAt": retrieved_at} for r in records]


def text_object_metadata(record):
    p = provenance_for(record)
    return {
        "source-url": record.get("url", ""),
        "licence": p["licence"],
        "licence-url": p["licenceUrl"],
        "attribution": p["attribution"],
    }
```

Add `provenance.py` to the Dockerfile `COPY` line.

- [ ] **Step 4: Wire the rescrape task**

Imports first (all four modules sit in the same directory, imported as siblings like `common`):
- `corpus.py`: `from provenance import text_object_metadata`
- `app.py`: `from datetime import datetime, timezone` and `from provenance import stamp`
- `treaties.py`: `from datetime import datetime, timezone` and `from provenance import PROMPT_ATTRIBUTION_PREAMBLE, stamp, text_object_metadata`
- `enrichment.py`: `from provenance import PROMPT_ATTRIBUTION_PREAMBLE`

`corpus.py`: delete `SEED_USER_AGENT`; `_save_seed_text_strict(s3_client, record, text)` uses `record["url"]` for the key and passes `Metadata=text_object_metadata(record)`; `backfill_seed_text` iterates `for url, record in sorted(seed_docs.items())`, calls `fetch_full_pdf_text(url)` and `_save_seed_text_strict(s3_client, record, text)`; `save_text` passes `Metadata=text_object_metadata({"url": url})`; `save_docs(s3_client, docs)` accepts a dict or list (`docs_list = sorted(docs.values() if isinstance(docs, dict) else docs, key=...)`). `common.fetch_full_pdf_text(url)` drops the `user_agent` parameter and the docstring about gov.ie.

`app.py` `main()`: `run_timestamp = datetime.now(timezone.utc).isoformat()` at the top (import both); after `merge_seed_docs`: `docs_list = stamp(updated_docs.values(), run_timestamp)`; `save_docs(s3_client, docs_list)`; `index_documents(docs_list, ...)` (drop the local `docs_list = sorted(...)`); `treaties.run(s3_client, anthropic_client, run_timestamp)`.

`enrichment.enrich_batch`: prompt starts `PROMPT_ATTRIBUTION_PREAMBLE + "\n\n" + "You are enriching..."`; document block gains `f"  Source URL: {url}\n"` after `Filename`.

`treaties.py`: `run(s3_client, anthropic_client, run_timestamp=None)` with `run_timestamp = run_timestamp or datetime.now(timezone.utc).isoformat()` as its first line, so the existing two-argument calls in `tests/test_treaties.py:468-475` and the `boom(s3, ac)` mock at `:506-515` keep working (change that mock to `boom(s3, ac, *a, **k)` so `app.main()` can pass the third argument); `stamped = stamp(merged, run_timestamp)` before `save_treaties(s3_client, bucket, stamped)` and `index_documents(stamped, ...)`; `save_treaty_text` takes `record` (or builds `{"url": ...}` from the caller's record) and passes `Metadata`; `_enrich_one` prompt gets the preamble and `f"Source URL: {record['url']}\n"`.

`algolia_index.build_records`: add to `base`:

```python
        for field in ("sourceOrganisation", "licence", "licenceUrl", "attribution", "retrievedAt"):
            base[field] = doc.get(field, "")
```

- [ ] **Step 5: eBrief monitor.** Add near the top of `ebrief_monitor/app.py` a `PROMPT_ATTRIBUTION_PREAMBLE` constant byte-identical to the rescrape one, plus:

```python
def _text_object_metadata(url: str) -> Dict[str, str]:
    return {
        "source-url": url,
        "licence": "CC BY 4.0",
        "licence-url": (
            "https://www.revenue.ie/en/corporate/using-revenue/"
            "reuse-of-public-sector-information/public-sector-information-licence.pdf"
        ),
        "attribution": (
            "Information provided courtesy of the Revenue Commissioners under a "
            "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
        ),
    }
```

`save_text_to_s3` passes `Metadata=_text_object_metadata(url)`; `_generate_with_bedrock` prompt starts with the preamble and includes `f"Source URL: {url}\n"` after `Filename`.

- [ ] **Step 6: Script.** `scripts/enrich-metadata.py`: add `sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda", "revenue_docs", "rescrape"))` and `from provenance import PROMPT_ATTRIBUTION_PREAMBLE`; prompt starts with it; document block gains `Source URL`; add `def should_enrich(doc): return doc.get("category") != "PRSI (gov.ie)"`. **Do not reassign `docs`**: the full `docs` list is what gets written back to `revenue-docs.json` at the end of the script (`scripts/enrich-metadata.py:225-233`), so filtering it would delete every gov.ie record. Introduce `docs_to_enrich = [d for d in docs if should_enrich(d)]` and use `docs_to_enrich` only for the text-loading pool and the batching loop; the final save still serialises `docs`. Test: run the script's main flow with a mocked S3 and client over two records (one gov.ie) and assert the saved list still has both and the client was called with only the Revenue record.

- [ ] **Step 7: Run everything.** `pytest -q && black --check . && isort --check-only . && flake8`. Expected: pass.

- [ ] **Step 8: Docs.** `README.md` Revenue Documents section: list the five record fields and the licence statement; replace the sentence claiming the rescrape image is built by "its own workflow" with: "The manual `tf-deploy-prod` workflow builds and pushes the rescrape image; `tf-deploy-stage` does not; `scripts/build-rescrape.sh` is for an independent manual push." `docs/revenue-documents-algolia-search.md` record shape: add the five fields.

- [ ] **Step 9: Commit** on `revenue-psi-attribution`: `git commit -m "feat(revenue-docs): stamp PSI Licence provenance on records, text objects and enrichment prompts"`.

---

## Rollout checklist (after each PR is approved and merged)

1. MCP: `deploy-stage` runs on merge. Call `get_revenue_document_text` on `mcp-stage.aws.irishtaxhub.ie` and confirm `attribution.source.statement`. Dispatch `deploy-prod`.
2. Web: check `/revenue-documents`, `/mcp` and the footer on the Vercel preview. Promote the `main` build in Vercel.
3. Platform: `deploy-stage` on merge; dispatch `deploy-prod`.
4. API: `deploy-stage` on merge. `curl https://stage.aws.irishtaxhub.ie/v1/revenue/documents/text/19-07-03 | jq .attribution`. Dispatch `deploy-prod` (before the next MCP deploy is irrelevant; MCP adopts the object at runtime).
5. Lambdas: `tf-deploy-stage` on merge (nothing runs on stage). Dispatch `tf-deploy-prod` (builds and pushes the rescrape image, deploys the monitor). After the Sunday run, `aws s3 cp s3://irish-tax-documents/revenue-docs.json - | jq '.[0] | {attribution, retrievedAt}'` and check a gov.ie record shows the Department of Social Protection.
6. Reply to McCann FitzGerald listing the surfaces and the removed user-agent workaround.
