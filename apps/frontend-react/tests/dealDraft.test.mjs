import { test } from "node:test";
import assert from "node:assert/strict";
import { buildDealDraft, sourceTrace } from "../src/lib/dealDraft.js";

test("source trace uses real file and row, never a synthesized csv name", () => {
  const trace = sourceTrace({
    source_dataset: "ITC_TradeMap",
    source_file: "output/raw/nipa_ict_buyer.csv",
    source_row_no: "42",
  });
  assert.equal(trace.status, "identified");
  assert.equal(trace.sourceFile, "output/raw/nipa_ict_buyer.csv");
  assert.equal(trace.sourceRowNo, "42");
  assert.equal(trace.sourceFile.includes("ITC_TradeMap.csv"), false);
});

test("missing provenance is explicit", () => {
  const trace = sourceTrace({ source_dataset: "ITC_TradeMap" });
  assert.equal(trace.status, "unavailable");
  assert.equal(trace.sourceFile, "원천 확인 불가");
  assert.equal(trace.sourceRowNo, "원천 확인 불가");
});

test("deal draft stays unsent and review-required when contact or source is incomplete", () => {
  const draft = buildDealDraft({
    buyer: {
      buyer_name: "Acme",
      source_dataset: "sns_scrape",
      country_norm: "vietnam",
      contact_email_estimated: true,
      contact_email: "guess@example.com",
      source_verification: "unverified",
    },
    hsCode: "330499",
    simulation: { profitUSD: 10, profitRate: 1.5 },
  });
  assert.equal(draft.sent, false);
  assert.equal(draft.stage, "dry_run");
  assert.equal(draft.reviewStatus, "REVIEW_REQUIRED");
  assert.ok(draft.reasons.includes("원천 확인 불가"));
  assert.ok(draft.reasons.includes("추정 연락처"));
  assert.ok(draft.reasons.includes("출처 미검증"));
  assert.equal(draft.marginSource, "사용자 입력");
  assert.equal(draft.hsCode, "330499");
});

test("complete provenance can be a dry-run deal without sending", () => {
  const draft = buildDealDraft({
    buyer: {
      buyer_name: "Acme",
      source_dataset: "kotra",
      source_file: "raw/a.csv",
      source_row_no: "7",
      source_verification: "verified",
      contact_email: "buy@acme.de",
      contact_email_estimated: false,
      country_norm: "germany",
    },
    hsCode: "330499",
  });
  assert.equal(draft.reviewStatus, "DRY_RUN");
  assert.equal(draft.sent, false);
  assert.deepEqual(draft.reasons, []);
  assert.equal(draft.sourceFile, "raw/a.csv");
  assert.equal(draft.sourceRowNo, "7");
});
