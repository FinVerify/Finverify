# FinVerifyBench Verification Track
# Deterministic Candidate Enumerator Implementation Specification

**Document:** `ENUMERATOR_SPEC_v1.md`  
**Version:** 1.0  
**Phase:** 9C-E — Enumerator Implementation Freeze  
**Status:** FINAL IMPLEMENTATION SPEC CANDIDATE  
**Parent methodology:** `SOURCE_ELIGIBILITY_v1.md` v1.0  
**Parent methodology freeze commit:** `7d28cb0ee68514b43f1d4d4d64f8a3489bd105fa`  
**Parent methodology SHA-256:** `7E19D2F11906D0723EBA65A4FC95DD1C79952DE09E475DDFC1D3898BE5C7AC03`

---

# 1. Purpose

This document defines the implementation contract for the deterministic
quantitative candidate enumerator required by `SOURCE_ELIGIBILITY_v1.md`.

The enumerator is infrastructure.

It does NOT determine scientific eligibility.

Its purpose is to transform frozen source artifacts into a deterministic,
high-recall raw occurrence ledger containing explicit quantitative occurrences
and sufficient provenance for later verifier-blind human eligibility review.

The required architecture is:

canonical source artifact
        ↓
deterministic parsing
        ↓
structural document representation
        ↓
quantitative occurrence detection
        ↓
occurrence normalization
        ↓
stable provenance
        ↓
stable candidate IDs
        ↓
raw candidate ledger

The enumerator MUST NOT:

- call FinVerify;
- call any LLM;
- call any model API;
- determine whether FinVerify can verify a candidate;
- assign scientific eligibility;
- remove candidates because they appear non-financial;
- deduplicate financial facts;
- perform DEV/TEST splitting;
- select Natural examples;
- select Controlled parents;
- create perturbations;
- run baselines;
- calculate experimental results.

---

# 2. Governing Documents

Implementation MUST conform to:

1. `PROTOCOL.md`
2. `EXPERIMENT_SPEC_v1.md`
3. `SOURCE_ELIGIBILITY_v1.md`
4. Phase 8 verification infrastructure
5. Phase 9B frozen source manifest

If this implementation specification conflicts with
`SOURCE_ELIGIBILITY_v1.md`, the frozen eligibility protocol takes precedence.

The implementation MUST NOT modify a frozen upstream scientific contract merely
to simplify engineering.

---

# 3. Scientific Information Barrier

During implementation and testing of the enumerator, the implementation agent
MUST NOT run the enumerator on the 12 Phase 9B scientific source artifacts.

This restriction applies to:

`data/verification/sources/**`

The implementation agent MUST NOT:

- inspect enumerator output from those artifacts;
- count detected occurrences in those artifacts;
- tune patterns based on those artifacts;
- manually inspect misses produced by those artifacts;
- modify extraction logic after observing their candidate distributions.

The scientific corpus may be inspected only as required to understand frozen
file-format inventory or existing provenance metadata already documented in the
repository.

Its quantitative contents MUST NOT be used to tune the enumerator.

All implementation development and testing MUST use synthetic fixtures.

---

# 4. No Network or External Model Dependency

Enumeration MUST be locally reproducible.

The scientific enumerator MUST NOT require:

- network access;
- web search;
- remote APIs;
- cloud OCR;
- LLM inference;
- embedding APIs;
- proprietary extraction services.

The final enumeration path must operate from frozen local source artifacts.

---

# 5. Required Implementation

The primary CLI entry point MUST be:

`scripts/enumerate_verification_candidates.py`

Reusable implementation SHOULD live inside the existing:

`verification/`

package.

Recommended module structure:

`verification/enumeration/__init__.py`

`verification/enumeration/models.py`

`verification/enumeration/parser.py`

`verification/enumeration/html_parser.py`

`verification/enumeration/pdf_parser.py`

`verification/enumeration/numeric.py`

`verification/enumeration/normalization.py`

`verification/enumeration/provenance.py`

`verification/enumeration/ledger.py`

The exact internal split may differ if the repository architecture strongly
supports a simpler design.

However, parsing, numeric detection, provenance construction, and ledger
serialization MUST remain logically separable and independently testable.

---

# 6. Supported Source Formats

The Phase 9B corpus requires support for:

- `.html`
- `.mhtml`
- `.pdf`

Unsupported formats MUST fail explicitly.

They MUST NOT be silently ignored.

---

# 7. Canonical Source Identity

Each enumeration input MUST correspond to an artifact registered in:

`data/verification/source_manifest.json`

The enumerator MUST use the manifest as the source of:

- `source_id`;
- canonical relative path;
- expected SHA-256;
- company/ticker metadata where provided;
- reporting metadata where provided.

Before parsing an artifact, its actual SHA-256 MUST be compared with the
manifest hash.

A mismatch MUST cause a hard failure for that artifact.

The enumerator MUST NOT enumerate from bytes whose hash differs from the
canonical manifest.

---

# 8. Deterministic Parsing

Given:

- identical source bytes;
- identical manifest;
- identical enumerator code;
- identical dependency versions;

the parser MUST produce identical structural output.

Parsing MUST NOT contain:

- random sampling;
- nondeterministic ordering;
- model inference;
- environment-dependent candidate ordering.

Where a dependency exposes nondeterministic behavior, the implementation must
normalize or explicitly control it.

---

# 9. Internal Structural Representation

All source formats SHOULD be transformed into a common logical representation.

The representation should support elements such as:

- document;
- heading;
- paragraph;
- sentence/text block;
- table;
- table row;
- table cell;
- transcript-like utterance where detectable;
- metadata.

Each structural node SHOULD have a deterministic locator.

The exact internal Python representation is an engineering choice.

The scientific requirement is that each extracted numerical occurrence can be
traced deterministically back to its canonical source.

---

# 10. HTML Parsing

HTML parsing MUST:

- extract visible textual content;
- preserve document order;
- preserve headings;
- preserve paragraph/block boundaries;
- preserve table structure;
- preserve row/column relationships where structurally available;
- exclude non-content elements such as scripts and styles.

The parser MUST NOT use CSS rendering or browser automation as a scientific
requirement.

Hidden boilerplate may be retained if deterministic removal cannot be safely
established.

High recall is preferred to aggressive cleaning.

---

# 11. MHTML Parsing

MHTML parsing MUST deterministically identify and parse the primary document
content.

The implementation must:

- parse MIME structure locally;
- identify the primary HTML/text representation;
- avoid remote resource fetching;
- preserve source provenance.

Images, stylesheets, and unrelated binary MIME parts do not require numerical
enumeration unless they contain machine-readable textual content already
represented in the primary document.

---

# 12. PDF Parsing

PDF enumeration MUST use deterministic local text extraction.

The implementation MUST preserve page provenance.

At minimum, every PDF-derived occurrence must retain:

`page_number`

or an equivalent deterministic page locator.

The parser SHOULD preserve:

- text blocks;
- lines;
- table-like structural relationships where reliably recoverable.

The implementation MUST NOT require OCR for the frozen enumerator unless a
separate protocol amendment explicitly authorizes it.

If a page or region cannot yield reliable machine-readable text, the condition
must be represented as a parse/recovery issue rather than silently reconstructed
with an LLM or OCR service.

---

# 13. PDF Table Limitation

PDF table reconstruction is inherently imperfect.

The enumerator is therefore NOT required to infer financial meaning from PDF
layout.

It IS required to preserve as much deterministic structural information as the
chosen parser reliably exposes.

If reliable row/column structure cannot be recovered, later eligibility review
may classify an occurrence under the frozen table-context rules.

The enumerator MUST NOT invent table relationships.

---

# 14. Frozen Quantitative Lexical Grammar

Candidate enumeration MUST implement the lexical grammar defined in this
section.

Implementations may use regular expressions, a lexer, parser combinators, or
equivalent deterministic mechanisms, but the accepted textual forms and
precedence rules defined here are normative.

Matching is performed over Unicode text after parser-level structural
extraction but before scientific eligibility review.

The enumerator MUST preserve the exact matched substring as
`target_raw_text`.

The grammar is intentionally syntactic and high-recall.

It MUST NOT infer financial concepts.

## 14.1 NUMBER

`NUMBER` consists of:

- optional explicit sign: `+` or `-`;
- digits with optional comma grouping;
- optional decimal fraction.

Accepted examples:

`12`
`12.5`
`1,250`
`1,250.75`
`+12`
`-12.5`

Comma grouping MUST use groups of three digits after the first group.

Malformed groupings such as:

`12,34`
`1,2,3`

MUST NOT be interpreted as a single NUMBER.

## 14.2 ACCOUNTING_NUMBER

A NUMBER enclosed in parentheses MAY represent a syntactically negative
accounting quantity when used as part of a currency/scaled financial form.

Example:

`($2.1B)`

Its normalized sign is negative.

The exact parentheses remain part of `target_raw_text`.

## 14.3 SCALE

The following scale tokens are recognized case-insensitively for full words:

`thousand`
`million`
`billion`
`trillion`

The following abbreviated scale tokens are recognized:

`K`
`M`
`B`
`T`

An abbreviated scale token must be directly adjacent to the number or separated
from it only by whitespace.

## 14.4 CURRENCY_MARKER

Recognized explicit currency markers are:

`$`
`US$`
`USD`

The marker may immediately precede NUMBER or be separated by whitespace where
the textual form permits it.

The frozen enumerator does not infer currency from context when no explicit
currency marker exists.

## 14.5 CURRENCY

A currency occurrence is:

`CURRENCY_MARKER + NUMBER [+ SCALE]`

or its valid accounting-parenthetical equivalent.

Examples:

`$39.3 billion`
`$39.3B`
`$39,300 million`
`$39,300M`
`$391,035`
`US$39.3 billion`
`USD 39.3 billion`
`-$2.1B`
`($2.1B)`

## 14.6 PERCENTAGE

A percentage occurrence is either:

`NUMBER + %`

or:

`NUMBER + whitespace + percent`

The word `percent` is matched case-insensitively.

Examples:

`12%`
`12.0%`
`-12%`
`+12%`
`12 percent`

## 14.7 BASIS_POINTS

A basis-point occurrence is:

`NUMBER + whitespace + bps`

or:

`NUMBER + whitespace + basis point`

or:

`NUMBER + whitespace + basis points`

Word forms are matched case-insensitively.

Examples:

`50 bps`
`+50 bps`
`-50 bps`
`50 basis points`

## 14.8 RATIO

A ratio occurrence is:

`NUMBER + x`

with `x` directly adjacent to the number,

or:

`NUMBER + whitespace + times`

where `times` is matched case-insensitively.

Examples:

`1.5x`
`12.4 times`

## 14.9 SCALED_NUMBER

A scaled-number occurrence is:

`NUMBER + SCALE`

where no explicit currency marker is present.

Examples:

`2.5 million`
`10B`

This is a syntactic category only.

## 14.10 PER-SHARE CONTEXT

The enumerator MUST NOT create a separate inferred numerical value for
per-share semantics.

When an explicit currency occurrence appears in deterministic local text
containing one of the following case-insensitive lexical forms:

`per share`
`per diluted share`
`per basic share`
`EPS`
`earnings per share`

the occurrence MAY additionally receive syntactic kind:

`per_share_numeric`

The underlying explicit target remains the matched numeric/currency substring.

No financial ground-truth concept is inferred.

## 14.11 PLAIN NUMBER

A NUMBER not consumed by a higher-precedence quantitative form is emitted as:

`number`

provided it occurs in visible document text rather than parser-excluded
technical content.

This intentionally retains dates, years, counts, and other potentially
ineligible quantities for later human review.

## 14.12 Matching Precedence

At any character position, overlapping matches MUST be resolved using the
following precedence:

1. currency;
2. percentage;
3. basis_points;
4. ratio;
5. scaled_number;
6. number.

The longest valid match within the highest-precedence category MUST be selected.

Characters consumed by one emitted target MUST NOT independently generate
nested targets from the same character span.

Example:

`$39.3B`

produces one currency target, not:

`$39.3B`
`39.3B`
`39.3`

## 14.13 Ranges

A range connector does not form a single quantitative target.

Recognized connectors are:

`to`
`-`
`–`
`—`

when occurring between two independently valid quantitative expressions.

Each endpoint MUST be emitted separately.

No midpoint, width, or derived quantity may be emitted.

## 14.14 Multiple Quantities

Every non-overlapping explicit quantitative target receives its own candidate
record.

A source span containing three explicit quantitative targets therefore
produces three candidate records.

## 14.15 No Derived Quantities

Only text explicitly present in the source may produce a target.

The enumerator MUST NOT calculate or emit unstated:

- growth rates;
- differences;
- margins;
- averages;
- midpoints;
- range widths;
- ratios;
- percentage changes.

---

# 22. Ranges

Explicit numeric ranges MUST yield separate targeted occurrences.

Example:

`$73.7B to $74.8B`

produces:

- `$73.7B`
- `$74.8B`

The enumerator MUST NOT create:

- midpoint;
- width;
- average;
- implied change.

Range-role interpretation occurs later.

---

# 23. Multi-Number Source Spans

Every explicit target occurrence receives its own candidate record.

Example:

`Revenue was $39.3 billion, up 12% sequentially and 78% year over year.`

must produce three target occurrences.

The records may share the same source span.

Each record must preserve a distinct target locator.

---

# 24. No Researcher Arithmetic

The enumerator MUST NOT generate numbers absent from the source.

It MUST NOT calculate:

- growth rates;
- differences;
- margins;
- averages;
- midpoints;
- range widths;
- percentage changes;
- ratios.

Only explicit textual quantitative occurrences are enumerated.

Representation normalization is allowed.

Financial derivation is not.

---

# 25. Deterministic Raw Source Span Construction

`raw_source_span` MUST be constructed deterministically from the structural
text unit produced by the format parser.

The enumerator MUST NOT depend on an external statistical or learned sentence
tokenizer.

For prose-like structural blocks, sentence segmentation uses the following
frozen procedure:

1. normalize CRLF and CR line endings to LF for parser-internal text handling;
2. preserve all other source-visible characters;
3. scan the structural block from left to right;
4. a sentence boundary occurs after `.`, `?`, or `!` when:
   - the punctuation is followed by whitespace or the end of the structural
     block; and
   - the punctuation is not located between two decimal digits;
5. consecutive terminal punctuation belongs to the preceding sentence;
6. leading and trailing whitespace surrounding the resulting segment is
   removed;
7. internal whitespace is preserved as produced by the deterministic parser.

If no sentence boundary surrounds the target, the complete structural block is
used.

For table-derived targets, `raw_source_span` MUST be the exact deterministic
text of the target cell.

Table row, column, heading, and neighboring structural context MUST be stored
separately in provenance fields and MUST NOT be concatenated into
`raw_source_span`.

The same segmentation function MUST be used for HTML, MHTML, and PDF
prose-like structural blocks after format-specific structural extraction.

No abbreviation dictionary, statistical tokenizer, LLM, or language model may
alter sentence boundaries.

Target offsets are Python Unicode code-point offsets into the resulting
`raw_source_span`.

The invariant:

`raw_source_span[target_start:target_end] == target_raw_text`

MUST hold for every candidate.

---

# 26. Target Locator

When multiple values occur within the same source span, the target MUST be
unambiguously identified.

At minimum preserve:

- target raw text;
- target start offset;
- target end offset;

relative to the stored raw source span where possible.

Offsets MUST use a documented indexing convention.

Recommended convention:

Python Unicode string code-point offsets using:

`raw_source_span[start:end]`

The following invariant MUST hold whenever offsets are available:

`raw_source_span[target_start:target_end] == target_raw_text`

---

# 27. Provenance

Every candidate must retain sufficient provenance to locate the source
occurrence.

Required fields include:

- `candidate_id`;
- `source_id`;
- `source_sha256`;
- `relative_path`;
- `source_format`;
- `source_locator`;
- `raw_source_span`;
- `target_raw_text`;
- target offsets where available;
- normalized numeric representation;
- parser metadata necessary for reproduction.

Format-specific provenance SHOULD additionally include:

HTML/MHTML:
- structural node path or equivalent;
- heading context where available;
- table coordinates where applicable.

PDF:
- page number;
- deterministic text/block locator where available.

---

# 28. Frozen Candidate ID Construction

Candidate IDs MUST use the following deterministic construction.

First construct the canonical identity payload as UTF-8 text:

`schema_version + "\n" +
 source_id + "\n" +
 source_locator + "\n" +
 str(target_start) + "\n" +
 str(target_end) + "\n" +
 target_raw_text`

No additional whitespace or fields may be inserted.

Compute:

`SHA256(payload.encode("utf-8")).hexdigest()`

The candidate ID is:

`fvq1_` followed by the lowercase 64-character SHA-256 hexadecimal digest.

Therefore:

`candidate_id = "fvq1_" + sha256(payload_utf8).hexdigest()`

`source_locator` MUST itself be produced by the frozen deterministic
format-specific locator rules implemented and tested by the enumerator.

For table cells and other structural units where the target occupies the entire
`raw_source_span`, offsets still refer to the target substring within that
span.

Candidate IDs MUST NOT incorporate:

- filesystem absolute paths;
- timestamps;
- machine names;
- extraction run number;
- dataset split;
- eligibility;
- FinVerify results;
- candidate ordering.

Two executions over identical canonical inputs MUST produce identical candidate
IDs.

# 28A. Frozen Source Locator Grammar

Source locators MUST be deterministic strings using forward slashes and
zero-based structural indices.

HTML/MHTML prose:

`block/<block_index>`

HTML/MHTML table cells:

`table/<table_index>/row/<row_index>/cell/<cell_index>`

PDF prose:

`page/<page_index>/block/<block_index>`

PDF table cells, only where deterministic table structure is actually exposed:

`page/<page_index>/table/<table_index>/row/<row_index>/cell/<cell_index>`

Indices are assigned strictly in parser-emitted document order after exclusion
of non-content technical nodes defined by this specification.

`page_index` is zero-based internally.

Human-facing provenance MAY additionally store one-based `page_number`.

If a PDF parser does not expose reliable table structure, the content MUST use
the PDF prose/block locator rather than inventing table coordinates.

No source locator may contain:

- memory addresses;
- absolute filesystem paths;
- parser-generated random IDs;
- timestamps;
- machine-specific values.

---

# 29. Candidate Ordering

Ledger ordering MUST be deterministic.

Recommended primary ordering:

1. manifest source order or stable `source_id`;
2. source structural order;
3. target occurrence order within source span.

Candidate ordering MUST NOT depend on filesystem enumeration order unless that
order is explicitly sorted.

---

# 30. Raw Candidate Schema

The raw ledger schema MUST be versioned.

Recommended top-level fields:

`schema_version`

`candidate_id`

`source_id`

`source_sha256`

`relative_path`

`source_format`

`source_locator`

`raw_source_span`

`target_raw_text`

`target_start`

`target_end`

`numeric_kind`

`normalized_value`

`normalized_unit`

`scale`

`parser_metadata`

`enumeration_status`

The exact serialization details may integrate with existing Phase 8 schemas,
but the scientific information above must not be lost.

---

# 31. Numeric Kind

The enumerator MAY assign syntactic numeric categories such as:

- `currency`
- `percentage`
- `basis_points`
- `per_share_numeric`
- `ratio`
- `scaled_number`
- `number`

These are syntactic extraction labels.

They are NOT scientific financial concepts.

For example:

`currency`

does not imply:

`Revenue`.

---

# 32. Enumeration Status

Raw extracted occurrences should use a neutral status such as:

`ENUMERATED`

The enumerator MUST NOT assign:

- `ELIGIBLE`;
- `EXCLUDED`;
- `ADJUDICATION_REQUIRED`.

Those statuses belong to later verifier-blind human eligibility review.

---

# 33. JSONL Output

Scientific raw candidate output MUST use deterministic JSONL.

Requirements:

- one candidate per line;
- UTF-8;
- stable key serialization where practical;
- deterministic record ordering;
- no timestamp fields that change output hashes between identical runs.

Running the enumerator twice on identical input MUST produce byte-identical
scientific JSONL output.

---

# 34. Deterministic Summary

The CLI MAY produce a separate summary containing:

- number of source artifacts;
- parser failures;
- raw occurrence count;
- counts by syntactic numeric kind.

Such summaries MUST NOT influence enumeration behavior.

Scientific candidate output MUST remain deterministic.

---

# 35. Failure Handling

The enumerator MUST distinguish:

1. artifact-level hard failure;
2. recoverable region-level parse limitation;
3. successful enumeration.

Examples of artifact-level hard failure:

- manifest hash mismatch;
- missing artifact;
- unsupported required format;
- unreadable file.

Hard failures MUST produce non-zero CLI exit status.

The enumerator MUST NOT silently continue and present an incomplete scientific
corpus as complete.

---

# 36. Parse-Issue Ledger

Recoverable parsing limitations SHOULD be recorded separately from candidate
records.

Recommended artifact:

`parse_issues.jsonl`

Each issue should preserve:

- source ID;
- locator;
- issue type;
- deterministic description.

Parse issues MUST NOT contain model-generated reconstruction.

---

# 37. No Silent Candidate Filtering

The enumerator MUST NOT filter an occurrence because it appears to be:

- a date;
- a page number;
- an employee count;
- a delivery count;
- operational;
- non-financial;
- irrelevant;
- duplicate.

If it matches the frozen broad syntactic enumeration rules, it belongs in the
raw ledger.

Later eligibility review handles exclusion.

Reasonable lexical safeguards that define the numeric grammar itself are
permitted.

---

# 38. Avoid Pathological Number Extraction

High recall does not require extracting every sequence of digits.

The detector should avoid obvious non-quantitative machine artifacts where
deterministically identifiable, such as:

- HTML IDs;
- CSS values;
- script contents;
- URL query numbers;
- MIME boundaries;
- binary encodings.

This is parser sanitation, not scientific eligibility filtering.

---

# 39. Boilerplate

Document boilerplate may contain numeric values.

The implementation may remove clearly non-visible/non-document technical
content such as:

- scripts;
- styles;
- MIME metadata;
- binary resources.

It should NOT aggressively remove visible document content based on subjective
relevance.

---

# 40. Synthetic Test Fixtures

Implementation tests MUST use synthetic fixtures only.

Required synthetic formats:

- HTML prose;
- HTML table;
- MHTML;
- PDF prose;
- PDF multi-number content;
- PDF/table-like content where supported.

Fixtures MUST NOT copy quantitative sentences from the 12 scientific source
artifacts.

They should be clearly artificial.

Example fictional entities may be used.

---

# 41. Required Numeric Tests

Synthetic tests MUST cover at least:

1. `$39.3 billion`
2. `$39.3B`
3. `$39,300M`
4. `12%`
5. `-12%`
6. `50 basis points`
7. `50 bps`
8. `$2.10 per diluted share`
9. `1.5x`
10. explicit numeric range
11. parenthetical negative currency
12. multiple numeric occurrences in one sentence.

The exact fictional values may differ.

---

# 42. Required Atomicity Test

A synthetic sentence containing at least three target quantities MUST produce
three candidate records.

The test MUST verify:

- shared source span where appropriate;
- distinct candidate IDs;
- correct target offsets;
- correct target raw text;
- source order preservation.

---

# 43. Required No-Derivation Test

Given synthetic source text containing:

`Revenue increased from $10B to $12B.`

the enumerator may extract:

- `$10B`
- `$12B`

but MUST NOT generate:

- `20%`;
- `$2B`;

unless those values explicitly appear in the fixture.

---

# 44. Required Table Test

A synthetic table fixture MUST verify preservation of:

- table identity;
- row context;
- column context;
- target cell;
- target occurrence.

The test should establish that the target value can be deterministically traced
back to its structural location.

---

# 45. Required Hash Test

A synthetic manifest/source pair MUST verify:

- matching SHA-256 → enumeration permitted;
- mismatching SHA-256 → hard failure.

The mismatch test MUST confirm that no scientific-style ledger is emitted as a
successful enumeration.

---

# 46. Required Determinism Test

Run the enumerator twice on identical synthetic input.

The resulting JSONL files MUST be byte-identical.

Their SHA-256 hashes MUST match.

Candidate IDs and ordering MUST be identical.

---

# 47. Required Manifest-Order Test

Synthetic artifacts presented through different filesystem enumeration orders
MUST still produce the same deterministic scientific ordering defined by the
implementation.

---

# 48. Required Non-Eligibility Test

Synthetic input should contain examples such as:

- year/date;
- employee count;
- operational quantity;
- financial amount.

If all match the broad frozen numeric grammar, the enumerator must retain them
as raw occurrences.

The test must demonstrate that the enumerator is NOT performing scientific
eligibility filtering.

---

# 49. Required Information-Barrier Test

The enumerator package and CLI MUST have no import or runtime dependency on the
frozen FinVerify verification path.

A focused test or static assertion should verify that enumeration does not call:

- verifier execution;
- verification result logic;
- model inference.

Implementation should prefer architectural separation over fragile string
checks.

---

# 50. Existing Infrastructure Compatibility

The implementation SHOULD reuse Phase 8 utilities where appropriate.

It MUST NOT duplicate existing deterministic JSONL, hashing, or schema
functionality without a concrete reason.

However, frozen Phase 7H verifier behavior MUST NOT be modified.

Phase 8 semantics MUST NOT be weakened to accommodate enumeration.

---

# 51. Frozen Files

Enumerator implementation MUST NOT modify the frozen verifier merely to support
candidate construction.

In particular, avoid changes to Phase 7H identity/provenance semantics unless a
separate verified conflict requires them.

The implementation should be additive within FinVerifyBench.

---

# 52. Existing Scientific Data

The implementation task MUST NOT modify:

`finverify-bench/data/seed_50.json`

or any existing benchmark dataset.

It MUST NOT modify:

`data/verification/sources/**`

It MUST NOT create a scientific candidate ledger from the real Phase 9B corpus
during implementation.

---

# 53. Test Isolation

Synthetic fixtures SHOULD live under a dedicated test fixture path, for example:

`tests/fixtures/enumeration/`

They must be obviously synthetic and must not be confused with scientific
corpus artifacts.

Generated temporary test output should use temporary directories.

---

# 54. Dependency Discipline

Prefer existing repository dependencies where technically adequate.

New dependencies may be added only when required for deterministic parsing.

Any new parsing dependency MUST be:

- version-identifiable;
- locally executable;
- deterministic enough for frozen enumeration;
- documented.

A dependency fingerprint MUST be recordable at freeze time.

Do not introduce large ML dependencies for document parsing.

---

# 55. CLI Contract

The CLI should support an interface equivalent to:

`python scripts/enumerate_verification_candidates.py --manifest <manifest> --output <ledger.jsonl> --issues <parse_issues.jsonl>`

Optional arguments may include:

`--source-root`

or equivalent path configuration.

The default scientific path MAY point toward the frozen manifest, but
implementation tests MUST invoke only synthetic manifests.

The implementation agent MUST NOT execute the CLI against the real manifest
during this phase.

---

# 56. Mandatory Development Safety Guard

Before the enumerator implementation is scientifically frozen, execution
against the canonical Phase 9B scientific corpus MUST be programmatically
blocked.

The canonical production corpus is identified by BOTH:

1. the canonical manifest path:

   `data/verification/source_manifest.json`

2. the frozen Phase 9B source identities and SHA-256 values represented by that
   manifest.

The CLI MUST refuse production-corpus enumeration by default.

Before implementation freeze there MUST NOT exist a normal CLI option, flag,
environment variable, configuration value, or alternate code path that allows
the development agent to bypass this restriction.

Synthetic manifests and synthetic source artifacts remain executable.

Production authorization MUST be introduced only after:

- implementation completion;
- synthetic test completion;
- blocker-focused implementation audit;
- regression testing;
- enumerator freeze commit.

The authorization mechanism introduced after freeze MUST be an explicit,
documented code change or versioned production-enablement step whose commit is
recorded before the first canonical scientific enumeration.

The development safety guard MUST NOT alter parsing or extraction semantics.
It exists only to enforce the scientific information barrier.

# 57. Production Authorization

The implementation phase ends before scientific enumeration.

After:

- implementation completion;
- synthetic tests;
- implementation audit;
- regression tests;
- enumerator freeze commit;

the production safety guard may be explicitly enabled/unlocked according to a
documented procedure.

The first run against the 12 canonical source artifacts is a separate
scientific event.

---

# 58. Enumerator Freeze Report

Implementation MUST produce:

`PHASE9C_ENUMERATOR_FREEZE_REPORT.md`

The report must record:

- starting commit;
- governing protocol/spec hashes;
- files added/modified;
- parser dependencies;
- synthetic fixture inventory;
- focused test results;
- FinVerifyBench regression results;
- relevant backend regression results if applicable;
- confirmation that frozen verifier files were not modified;
- confirmation that scientific source artifacts were not modified;
- confirmation that the enumerator was NOT run against the real Phase 9B
  corpus;
- known parser limitations;
- remaining CRITICAL/HIGH findings;
- final freeze verdict.

---

# 59. Pre-Freeze Audit

Before the enumerator is frozen, perform a blocker-focused implementation audit.

The audit must verify:

1. conformity with `SOURCE_ELIGIBILITY_v1.md`;
2. deterministic parsing;
3. high-recall numeric enumeration;
4. no scientific eligibility filtering;
5. stable candidate IDs;
6. deterministic ordering;
7. provenance completeness;
8. table provenance behavior;
9. source hash validation;
10. no researcher arithmetic;
11. no FinVerify dependency;
12. no real-corpus execution during development;
13. synthetic-only testing;
14. byte-identical repeated output;
15. frozen upstream files remain intact.

Any CRITICAL/HIGH finding must be resolved before freeze.

---

# 60. Definition of Done

Enumerator implementation is complete when:

- [ ] required parser support exists for HTML;
- [ ] required parser support exists for MHTML;
- [ ] required parser support exists for PDF;
- [ ] broad quantitative extraction is implemented;
- [ ] explicit values remain explicit;
- [ ] no researcher arithmetic occurs;
- [ ] multi-number atomicity works;
- [ ] raw source spans are preserved;
- [ ] target offsets are deterministic;
- [ ] source provenance is preserved;
- [ ] manifest SHA-256 is validated;
- [ ] candidate IDs are stable;
- [ ] candidate ordering is deterministic;
- [ ] JSONL output is byte-deterministic;
- [ ] parse failures are explicit;
- [ ] scientific eligibility is not assigned;
- [ ] duplicate resolution is not performed;
- [ ] FinVerify is not called;
- [ ] synthetic tests pass;
- [ ] determinism tests pass;
- [ ] relevant regressions pass;
- [ ] implementation audit has no CRITICAL/HIGH blockers;
- [ ] enumerator was not run against the real Phase 9B corpus;
- [ ] freeze report exists;
- [ ] implementation freeze commit is recorded.

---

# 61. Post-Freeze Scientific Run

Only after the enumerator implementation is frozen may it be run against:

`data/verification/source_manifest.json`

and the canonical Phase 9B source corpus.

The first scientific enumeration MUST:

1. begin from a clean frozen enumerator commit;
2. validate all source hashes;
3. process all 12 artifacts;
4. produce the raw candidate ledger;
5. produce parse-issue records;
6. produce deterministic summary statistics;
7. immediately compute SHA-256 for scientific outputs;
8. preserve the exact outputs;
9. commit/freeze the enumeration artifacts before human eligibility decisions.

The enumerator MUST NOT be modified after inspecting scientific output merely
to improve candidate composition.

---

# 62. Post-Run Defect Rule

If the first scientific run exposes an actual implementation defect rather than
an undesirable candidate distribution, the defect MUST NOT be silently fixed.

A defect means the implementation violates this frozen specification.

Examples:

- offsets are incorrect;
- parser crashes on a supported canonical artifact;
- manifest-valid source cannot be processed because of an implementation bug;
- explicit supported numeric syntax is systematically lost because the
  implementation contradicts its frozen grammar;
- candidate IDs are nondeterministic.

A defect does NOT mean:

- too many false positives;
- too few attractive financial examples;
- undesirable company balance;
- too many operational numbers;
- FinVerify may struggle with the candidates.

Any genuine post-run defect requires:

1. documented defect;
2. evidence that it violates the frozen implementation specification;
3. versioned implementation amendment;
4. rerun of the complete corpus;
5. preservation of prior outputs;
6. disclosure in the freeze history.

---

# 63. Final Principle

The enumerator is intentionally ignorant of the hypothesis.

It answers only:

> Where are the explicit quantitative occurrences in the frozen source corpus,
> and where exactly did each occurrence come from?

It does NOT answer:

> Is this a good benchmark example?

It does NOT answer:

> Can FinVerify verify this?

It does NOT answer:

> Should this example be in TEST?

Those decisions belong to later frozen stages.

The scientific sequence remains:

SOURCE_ELIGIBILITY_v1
        ↓
ENUMERATOR_SPEC_v1
        ↓
synthetic implementation
        ↓
enumerator freeze
        ↓
first canonical enumeration
        ↓
raw ledger freeze
        ↓
verifier-blind eligibility review
        ↓
deduplication/source grouping
        ↓
eligible pool freeze
        ↓
Phase 9D sampling freeze
        ↓
FinVerify execution