/**
 * Phone number validation / display helpers.
 * E.164-ish: digits only must be 7–15 chars.
 */
export function validatePhone(phone) {
  if (!phone || typeof phone !== "string") return false;
  const cleaned = phone.trim();
  if (cleaned.length === 0) return false;
  // Allow digits, +, -, spaces, parentheses
  if (!/[\d+\-\s()]+$/.test(cleaned)) return false;
  const digits = cleaned.replace(/\D/g, "");
  return digits.length >= 7 && digits.length <= 15;
}

export function displayPhone(phone) {
  return validatePhone(phone) ? phone.trim() : "-";
}

