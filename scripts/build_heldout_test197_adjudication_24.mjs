import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const scriptsDir = path.dirname(fileURLToPath(import.meta.url));
const repo = path.dirname(scriptsDir);
const heldoutDir = path.join(repo, "results", "heldout_test_197");
const frozenDir = path.join(heldoutDir, "annotations_frozen_v1");
const evidencePath = path.join(heldoutDir, "evidence_frozen_v1.jsonl");
const outputDir = path.join(heldoutDir, "adjudication_24_blind_v1");
const internalAuditPath = path.join(heldoutDir, "adjudication_24_blind_v1_BUILD_AUDIT.json");
const htmlTemplatePath = path.join(scriptsDir, "Feedback-lifecycle-audit_Adjudicator_24_BLIND.template.html");

const sourceFiles = {
  A01_csv: path.join(frozenDir, "A01", "feedback-lifecycle-audit_annotations_A01 (2).csv"),
  A01_json: path.join(frozenDir, "A01", "feedback-lifecycle-audit_annotations_A01 (2).json"),
  A02_csv: path.join(frozenDir, "A02", "feedback-lifecycle-audit_annotations_A02 (2).csv"),
  A02_json: path.join(frozenDir, "A02", "feedback-lifecycle-audit_annotations_A02 (2).json"),
};
const coreFields = [
  "original_validity",
  "target_state_t1",
  "lifecycle_label",
  "instructional_priority",
];
const reasonCodes = [
  "ORIGINAL_DIAGNOSIS_FALSE",
  "TARGET_PERSISTS",
  "TARGET_RESOLVED",
  "EVIDENCE_INCOMPLETE",
  "EVIDENCE_CONFLICT",
  "TARGET_MAPPING_AMBIGUOUS",
  "CLAIM_SCOPE_AMBIGUOUS",
  "NON_DIAGNOSTIC",
];

function sha256Buffer(value) {
  return createHash("sha256").update(value).digest("hex");
}

async function sha256File(filePath) {
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(filePath)) hash.update(chunk);
  return hash.digest("hex");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sanitizeEvidence(record) {
  return {
    item_id: record.item_id,
    transition_id: record.transition_id,
    packet_id: record.packet_id,
    packet_format_version: record.packet_format_version,
    packet_sha256: record.packet_sha256,
    packet_prepared_without_method_predictions: record.packet_prepared_without_method_predictions,
    problem_id: record.problem_id,
    language: record.language,
    problem_statement: record.problem_statement,
    focal_claim: record.claim_span,
    earlier: record.earlier,
    later: record.later,
    code_diff: record.code_diff,
    compiler: record.compiler,
    tests: record.tests,
    stored_judge_traces: record.stored_judge_traces,
    claim_relevant_trace: record.claim_relevant_trace,
    all_evidence_ids: record.all_evidence_ids,
  };
}

const freezeManifest = JSON.parse(
  await fs.readFile(path.join(frozenDir, "FREEZE_MANIFEST.json"), "utf8"),
);
const expectedHashes = {
  A01_csv: freezeManifest.annotators.A01.csv.sha256,
  A01_json: freezeManifest.annotators.A01.json.sha256,
  A02_csv: freezeManifest.annotators.A02.csv.sha256,
  A02_json: freezeManifest.annotators.A02.json.sha256,
};
const observedHashes = {};
for (const [key, filePath] of Object.entries(sourceFiles)) {
  observedHashes[key] = await sha256File(filePath);
  assert(observedHashes[key] === expectedHashes[key], `${key} no longer matches the freeze manifest`);
}

const a01 = JSON.parse(await fs.readFile(sourceFiles.A01_json, "utf8"));
const a02 = JSON.parse(await fs.readFile(sourceFiles.A02_json, "utf8"));
assert(Array.isArray(a01) && a01.length === 168, "A01 must contain 168 rows");
assert(Array.isArray(a02) && a02.length === 168, "A02 must contain 168 rows");
const a02ById = new Map(a02.map((row) => [row.item_id, row]));
assert(a02ById.size === 168, "A02 item IDs must be unique");

const disagreements = a01.map((row) => {
  const peer = a02ById.get(row.item_id);
  assert(peer, `A02 is missing ${row.item_id}`);
  const differingFields = coreFields.filter((field) => row[field] !== peer[field]);
  return { item_id: row.item_id, differingFields };
}).filter((entry) => entry.differingFields.length > 0);

const lifecycleCount = disagreements.filter((entry) => entry.differingFields.includes("lifecycle_label")).length;
const priorityOnlyCount = disagreements.filter(
  (entry) => entry.differingFields.length === 1 && entry.differingFields[0] === "instructional_priority",
).length;
assert(disagreements.length === 24, `Expected 24 disagreement cases; found ${disagreements.length}`);
assert(lifecycleCount === 23, `Expected 23 lifecycle disagreements; found ${lifecycleCount}`);
assert(priorityOnlyCount === 1, `Expected one priority-only disagreement; found ${priorityOnlyCount}`);

const selectedIds = disagreements.map((entry) => entry.item_id);
const selectedIdSet = new Set(selectedIds);
assert(selectedIdSet.size === 24, "Selected disagreement IDs must be unique");
const order = new Map(selectedIds.map((itemId, index) => [itemId, index]));

const selectedEvidence = [];
const input = createReadStream(evidencePath, { encoding: "utf8" });
const reader = readline.createInterface({ input, crlfDelay: Infinity });
for await (const line of reader) {
  if (!line.trim()) continue;
  const record = JSON.parse(line);
  if (!selectedIdSet.has(record.item_id)) continue;
  assert(record.packet_prepared_without_method_predictions === true,
    `${record.item_id} is not marked prediction-blind`);
  selectedEvidence.push(sanitizeEvidence(record));
}
assert(selectedEvidence.length === 24, `Expected 24 evidence packets; found ${selectedEvidence.length}`);
selectedEvidence.sort((left, right) => order.get(left.item_id) - order.get(right.item_id));
assert(new Set(selectedEvidence.map((record) => record.item_id)).size === 24,
  "Evidence packet item IDs must be unique");

const prohibitedKeys = new Set([
  "A01", "A02", "field_disagreements", "differing_fields", "lifecycle_disagreement",
  "predictions", "prediction", "model_output", "condition_B", "condition_C",
]);
function scanKeys(value, trail = []) {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => scanKeys(entry, [...trail, String(index)]));
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    assert(!prohibitedKeys.has(key), `Prohibited key in adjudicator packet: ${[...trail, key].join(".")}`);
    scanKeys(child, [...trail, key]);
  }
}
scanKeys(selectedEvidence);

const returnTemplate = selectedEvidence.map((record) => ({
  item_id: record.item_id,
  original_validity: "",
  target_state_t1: "",
  lifecycle_label: "",
  instructional_priority: "",
  confidence: null,
  reason_code: "",
  evidence_ids: [],
  adjudication_reason: "",
  adjudicator_id: "",
}));

const returnSchema = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  title: "Feedback-lifecycle-audit held-out TEST-197 blind adjudication return",
  type: "array",
  minItems: 24,
  maxItems: 24,
  items: {
    type: "object",
    additionalProperties: false,
    required: [
      "item_id", "original_validity", "target_state_t1", "lifecycle_label",
      "instructional_priority", "confidence", "reason_code", "evidence_ids",
      "adjudication_reason", "adjudicator_id",
    ],
    properties: {
      item_id: { type: "string", pattern: "^[0-9a-f]{24}$" },
      original_validity: { enum: ["SUPPORTED", "REFUTED", "INDETERMINATE"] },
      target_state_t1: { enum: ["PRESENT", "RESOLVED", "INDETERMINATE", "NOT_APPLICABLE"] },
      lifecycle_label: { enum: ["KEEP", "RETIRE", "RETRACT", "UNSURE"] },
      instructional_priority: { enum: ["HIGH", "LOW", "UNKNOWN"] },
      confidence: { type: "integer", minimum: 1, maximum: 5 },
      reason_code: { enum: reasonCodes },
      evidence_ids: {
        type: "array", minItems: 1, uniqueItems: true,
        items: { type: "string", minLength: 1 },
      },
      adjudication_reason: { type: "string", minLength: 1 },
      adjudicator_id: { type: "string", minLength: 1 },
    },
  },
};

await fs.mkdir(outputDir, { recursive: true });
const evidenceJson = `${JSON.stringify(selectedEvidence, null, 2)}\n`;
const evidenceJsonl = `${selectedEvidence.map((record) => JSON.stringify(record)).join("\n")}\n`;
const templateJson = `${JSON.stringify(returnTemplate, null, 2)}\n`;
const schemaJson = `${JSON.stringify(returnSchema, null, 2)}\n`;
const selectedIdsSha256 = sha256Buffer(`${selectedIds.join("\n")}\n`);
const evidenceGzipBase64 = gzipSync(Buffer.from(evidenceJsonl, "utf8"), { level: 9 }).toString("base64");
const htmlTemplate = await fs.readFile(htmlTemplatePath, "utf8");
const html = htmlTemplate
  .replace("__EMBEDDED_PACKET_GZIP_BASE64__", evidenceGzipBase64)
  .replace("__SELECTED_IDS_SHA256__", selectedIdsSha256);
assert(!html.includes("__EMBEDDED_PACKET_GZIP_BASE64__"), "Embedded packet placeholder was not replaced");
assert(!html.includes("__SELECTED_IDS_SHA256__"), "Selected-ID hash placeholder was not replaced");
const embeddedScript = html.match(/<script>([\s\S]*)<\/script>/);
assert(embeddedScript, "Generated HTML is missing its script block");
new Function(embeddedScript[1]);

const readme = `# Feedback-lifecycle-audit blind adjudication packet — 24 cases

Open \`Feedback-lifecycle-audit_Adjudicator_24_BLIND.html\` in a current Chrome or Edge browser.
The tool is self-contained, saves unfinished work in that browser, validates the
decision table, and exports the required 24-row JSON or JSONL return.

Review every case de novo. Use only the displayed frozen evidence: problem,
focal claim, S_t, S_t+1, code diff, compiler output, official tests and outputs,
stored judge traces, and any claim-relevant trace. Do not consult A01, A02, Qwen,
DeepSeek, or any other method output. None of those decisions or outputs is
included in this packet.

Required return fields, in order:

1. item_id
2. original_validity
3. target_state_t1
4. lifecycle_label
5. instructional_priority
6. confidence
7. reason_code
8. evidence_ids
9. adjudication_reason
10. adjudicator_id

The blank machine-readable template is \`adjudication_return_template_24.json\`.
The allowed values are enforced by \`adjudication_return_schema.json\` and by the
browser tool. The evidence is also supplied separately as JSON and JSONL for
auditability.
`;

const outputFiles = {
  "Feedback-lifecycle-audit_Adjudicator_24_BLIND.html": html,
  "adjudication_evidence_24.json": evidenceJson,
  "adjudication_evidence_24.jsonl": evidenceJsonl,
  "adjudication_return_template_24.json": templateJson,
  "adjudication_return_schema.json": schemaJson,
  "README.md": readme,
};
for (const [name, content] of Object.entries(outputFiles)) {
  await fs.writeFile(path.join(outputDir, name), content, "utf8");
}

const outputHashes = {};
for (const name of Object.keys(outputFiles)) {
  outputHashes[name] = await sha256File(path.join(outputDir, name));
}
const packetManifest = {
  status: "READY_FOR_BLIND_QUALIFIED_ADJUDICATION",
  case_count: 24,
  selected_item_ids_sha256: selectedIdsSha256,
  source_evidence: "../evidence_frozen_v1.jsonl",
  source_evidence_sha256: await sha256File(evidencePath),
  packet_prepared_without_method_predictions_all_true: true,
  human_annotation_values_included: false,
  disagreement_field_metadata_included: false,
  model_outputs_included: false,
  html_script_syntax_check_passed: true,
  output_sha256: outputHashes,
};
await fs.writeFile(
  path.join(outputDir, "MANIFEST.json"),
  `${JSON.stringify(packetManifest, null, 2)}\n`,
  "utf8",
);

const buildAudit = {
  status: "PASS",
  frozen_annotation_exports_unchanged: true,
  observed_annotation_export_sha256: observedHashes,
  row_count_per_annotator: 168,
  core_fields_compared: coreFields,
  unique_core_field_disagreement_count: disagreements.length,
  lifecycle_disagreement_count: lifecycleCount,
  priority_only_disagreement_count: priorityOnlyCount,
  selected_item_ids: selectedIds,
  adjudicator_packet: path.relative(repo, outputDir),
  adjudicator_packet_contains_A01_or_A02_values: false,
  adjudicator_packet_contains_disagreement_field_metadata: false,
  adjudicator_packet_contains_model_outputs: false,
  html_script_syntax_check_passed: true,
};
await fs.writeFile(internalAuditPath, `${JSON.stringify(buildAudit, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  status: packetManifest.status,
  output_dir: path.relative(repo, outputDir),
  case_count: selectedEvidence.length,
  lifecycle_disagreement_count: lifecycleCount,
  priority_only_disagreement_count: priorityOnlyCount,
  frozen_annotation_exports_unchanged: true,
}, null, 2));
