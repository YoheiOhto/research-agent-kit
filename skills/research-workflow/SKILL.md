---
name: research-workflow
description: Plan approved research, connect the exact plan to a GitHub Issue, and share traceable results with reviewed PNG/SVG figures. Use for experiment planning, execution handoffs, result bundles, or explicitly requested experiment-result HTML summaries.
license: MIT
---

# Research workflow

Use the receiving project's instructions, approval process, runner and storage conventions. This skill supplies a workflow, not execution permission, a scheduler gate or installed plotting software. Preserve stricter human-only submission rules. A reporting request does not authorize another experiment or analysis.

When a concrete illustration is useful, read [the synthetic worked example](references/example.md). It connects a plan and Issue draft to a saved table, optional plotting code, provenance and a pending visual review; it grants no execution approval.

## Agree the plan and authority

Before scientific implementation or real processing, discuss and fix the question, comparison, input identities, splits, preprocessing, model/prompt versions, settings, seeds/repetitions, evaluation, uncertainty, failure handling, enumerated variants, resources, outputs, preservation and stopping conditions. Record relevant budgets, deadlines and execution location. Mark irrelevant conditions with reasons; do not fill unknowns with defaults from examples.

Use the project's existing plan. If no convention exists, propose `experiments/<id>/plan.md` and agree it with the user. Identify the boundary between approved conditions and later execution status before approval. Preserve the approved prefix unchanged; put results and operational history below the project's existing status heading. Amend scientific conditions through a new preserved version, rather than rewriting approval evidence.

The sequence is discussion → fixed plan → Issue reflecting that exact version → explicit human approval of its scientific implementation and execution. Prepare the Issue draft first. Post or update only when authorized for that repository and target; otherwise show the draft and wait. If Issue access is unavailable, preserve the local draft and report the blocker before implementation or execution.

The Issue should link the plan/version, describe the comparison in plain words, and state deliverables, limits and open decisions. Identify the exact approved version using the project's revision/digest mechanism. Record the actual approval, target, scope and deadline faithfully. An Issue, label, review, schedule, successful check or agent-written approval file is not a human decision. Preserve previous approvals; never manufacture or refresh one yourself.

## Implement and execute within that version

Reuse an existing runner and reviewed examples where they match the approved conditions. Check the resolved configuration, variants, model/prompt and inputs against the plan before execution. Use only the project's approved execution route and resources. Missing approval, unknown scientific conditions or a human-only execution boundary stop the dependent action; read-only investigation and lightweight synthetic checks may continue.

At submission, record the actual code commit SHA, effective settings, input versions, environment, run identifier, output location and job identifiers when applicable. Keep uncommitted changes explicit. A commit proves which implementation was saved, not that a run succeeded or a scientific result is valid.

Resume only compatible saved work. Diagnose failures without silently changing the question, data, settings or success criteria. Check remaining scope, usage and deadlines before retries. Follow the project's already-authorized resource adjustment policy; do not invent an exemption, a new hard limit or approval for transfers, dependency changes, deletion or cancellation.

## Preserve one traceable result bundle

Agree output classes, locations, preservation and capacity limits during planning. When the project has no layout, propose run outputs under `outputs/<experiment>/<run>/` and one reviewed bundle under `outputs/<experiment>/reports/<bundle>/`. These are suggestions to confirm, not permission to move existing data. Formal daily/weekly reports, when requested, can use `reports/daily/` and `reports/weekly/` separately.

Reuse the same intact bundle when evidence and interpretation are unchanged. Create a distinguishable new version when either changes, preserving earlier evidence. Prefer aggregate tables and bounded records over a file per item. Do not add competing plans, routine transcripts or parallel reports; do not invent retention periods or delete evidence to meet a size target.

Preserve the run/variant table, metrics, failed and missing cases, relevant logs, input identities, actual code SHA, environment/settings, and reproduction instructions. Link the Issue, plan, runs and bundle in both the status record and result summary. Never invent job identifiers. Do not substitute commit activity for execution evidence or treat missing results as negative findings.

## Make and inspect result figures

Use validated saved results and the approved aggregation. Label units, denominators, comparisons, coverage and uncertainty. Keep failed, missing, ambiguous and unjudged cases visible; do not selectively drop them or generalize an incomplete sample. A request to plot saved results does not authorize new scientific comparisons or model calls.

Preserve source tables, plotting code, effective plot settings and provenance alongside the figures. Export a PNG preview and SVG when vector output suits the figure and the available tool supports it. For raster-heavy or unsupported content, state the limitation; an SVG container does not make embedded pixels vector data. Do not claim a plotting package or exporter is installed without checking, or install it without the project's authorization.

Actually open and inspect the generated images before adopting the conclusion or sharing them as reviewed results. Check labels, scales, clipping, legends, uncertainty, missing cases and agreement with the source table. Inspect SVG rendering when supplying it. Record a short review note identifying the files/version, what was inspected, problems and any fixes. If no visual inspection is possible, mark the bundle draft and explain the gap. This skill provides no mechanical finalization receipt, and a review note cannot certify scientific correctness.

## Share only the requested form

Answer in chat by default: purpose, comparison, usable results, limitations and next decision, with links to the canonical Issue, plan and bundle. State actual checks and distinguish measurements from estimates.

Create HTML only after an explicit request. Agree an artifact destination with the receiving user; do not assume a personal home path or place explanatory pages in the project by default. Make the requested page self-contained, embedding reviewed plots and essential context. Preserve the original PNG/SVG, source tables, code and provenance in the result bundle. HTML does not replace that evidence or authorize new analyses. Reuse the agreed page/bundle when unchanged instead of generating another report for every interaction.
