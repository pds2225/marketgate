/** Provenance and dry-run deal draft for the export flow. No invented source files. */

export function sourceTrace(item = {}) {
  const sourceDataset = String(item.source_dataset || "").trim();
  const sourceFile = String(item.source_file || "").trim();
  const sourceRowNo = String(item.source_row_no || "").trim();
  const identified = Boolean(sourceDataset && sourceFile && sourceRowNo);
  return {
    sourceDataset: sourceDataset || "원천 확인 불가",
    sourceFile: sourceFile || "원천 확인 불가",
    sourceRowNo: sourceRowNo || "원천 확인 불가",
    status: identified ? "identified" : "unavailable",
  };
}

export function buildDealDraft({ buyer, hsCode, simulation } = {}) {
  const item = buyer || {};
  const trace = sourceTrace(item);
  const email = String(item.contact_email || "").trim();
  const reasons = [];
  if (trace.status !== "identified") reasons.push("원천 확인 불가");
  if (!email) reasons.push("연락처 없음");
  else if (item.contact_email_estimated) reasons.push("추정 연락처");
  if (item.source_verification !== "verified") reasons.push("출처 미검증");

  return {
    stage: "dry_run",
    sent: false,
    reviewStatus: reasons.length ? "REVIEW_REQUIRED" : "DRY_RUN",
    reasons,
    hsCode: String(hsCode || "").trim(),
    buyerName: String(item.buyer_name || "").trim() || "이름 미확인",
    country: item.source_target_country_name || item.country_norm || "원천 확인 불가",
    sourceDataset: trace.sourceDataset,
    sourceFile: trace.sourceFile,
    sourceRowNo: trace.sourceRowNo,
    contactEmail: email || "원천 확인 불가",
    marginSource: "사용자 입력",
    profitUSD: simulation?.profitUSD ?? null,
    profitRate: simulation?.profitRate ?? null,
  };
}
