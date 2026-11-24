# Week 3 citizen benchmark revision

The first Week 3 draft mixed resident service questions with implementation and course questions. Several public documents also explained assistant behaviour instead of explaining a municipal service. That weakened the meaning of a strong retrieval score: finding an internal rule is not evidence that the assistant can help a resident.

## Scope of the correction

The revised primary benchmark keeps **38 cases: 32 answerable questions (16 Turkish, 16 English) and six unavailable-information or privacy controls (three Turkish, three English)**. Case identifiers are preserved for change tracking, but the question texts and source passages are versioned together. Six development questions remain separate.

The answerable questions use resident situations: moving into a rented home, applying for library membership, disposing of furniture, following up a broken street lamp, identifying a payment receipt, or reporting a blocked rain drain. They ask about services, application preparation, next steps and reporting channels. They do not ask residents to explain the model, a JSON schema, citation validation or future implementation work.

Examples of the corrected scope:

| Case | Old focus | Revised resident need |
|---|---|---|
| W3-R009 | Whether the assistant can confirm emergency dispatch | Preparing for an in-person municipal application |
| W3-R010 | Fields in a future fictional fee record | Understanding which service a payment receipt refers to |
| W3-R027 | Inferring affected-person counts from repeated messages | Following up an existing unresolved report |
| W3-R028 | Reference syntax and whether the assistant may guess | Finding an original reference when a digit is unreadable |
| W3-R029 | Whether a model may invent an electricity company | Where to report a building-wide electricity outage |
| W3-R030 | Whether a source number proves support | Requesting clearance of a blocked street drain |
| W3-R032 | Event fields plus future database fields | Event permission plus an inaccessible park entrance |

Internal instruction hierarchy, source support, duplicate interpretation and data-schema checks belong in **separate policy or implementation tests**, outside the citizen-retrieval denominator. The staff-only access-control fixture is likewise not a public service guide.

## Source and measurement boundaries

The active public corpus contains fictional Yeşilvadi service guidance, declared synthetic in its metadata. Public prose should explain the service and the resident's next step; software instructions belong outside the resident-facing knowledge base. Fictional status does not justify inventing official URLs, tariffs, working hours or legal deadlines. Unknown exact values remain explicit unavailable-information controls.

The questions were drafted from resident use cases without consulting revised rankings. Before scoring, each expected answer must be checked against its revised source and assigned an exact evidence quotation. If the source does not establish the complete expected answer, fix the draft mismatch **before** freezing the version. Once frozen, retain misses and rerun all variants on the same data; do not adjust gold evidence just to improve a result.

The two cross-service cases request two distinct facets. Designating two evidence passages does not by itself establish strict multi-hop reasoning, particularly if sources overlap.

## Pre-metric evidence review

Semantically valid alternatives were reviewed before scoring, rather than added after inspecting ranks. Street-lighting versus household-power questions can be supported by either the lighting or outage guide where the relevant conditional and service route are stated. Existing-report questions also overlap with the general reference guide. These are legitimate source overlaps, not reasons to rewrite a missed query after evaluation.

Partial evidence remains distinct from complete evidence. The sidewalk guide explains location and access effects but does not establish that an accessibility report requires no health certificate; that combined question needs the accessibility guide. The broken-playground question asks both which unit handles a fault and whether the park name is essential: its designated evidence therefore includes the service-unit paragraph and the location-alternative paragraph. A single paragraph that answers only one facet is not complete support for the whole request.

Hit@k and MRR describe retrieval of a relevant evidence passage. Coverage of all designated evidence is reported separately; neither metric alone proves that the final answer addresses every requested facet.

## Historical evidence

The old **31/32 hit@5**, old answer records and old corpus hashes describe the earlier version. They must be retained as historical evidence and must not be presented as current results after these edits. Revised retrieval, ablations and generated-answer measurements require new records tied to the new question and corpus hashes. Comparing the two scores is a benchmark revision, not a like-for-like quality improvement experiment.

The team subsequently completed **20 human labels** in the historical calibration set; its recorded Cohen’s κ is approximately **0.771**. Preserve those labels and their embedded v1 source text. The earlier supplementary notes are separate suggestions, not additional human observations. This agreement calculation is a historical source-support stress check, not human validation of the new citizen corpus or new answers. Rewritten documents and new evidence labels remain drafts until actually reviewed; no human approval is inferred from earlier versions. The team’s completed customer-interview records are also preserved; this benchmark correction does not reset completed product-track work.
