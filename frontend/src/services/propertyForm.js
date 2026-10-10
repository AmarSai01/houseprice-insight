/**
 * Shared property fields and validation for Estimate and Compare flows.
 */

export const AREA_TYPE_OPTIONS = [
  "Super built-up  Area",
  "Built-up  Area",
  "Plot  Area",
  "Carpet  Area",
];

export function createInitialPropertyForm() {
  return {
    location: "",
    area_type: "Super built-up  Area",
    total_sqft: "",
    bhk: "",
    bath: "",
    balcony: "0",
    is_ready_to_move: true,
  };
}

/**
 * @param {Record<string, unknown>} form
 * @returns {{ valid: boolean, errors: Record<string, string> }}
 */
export function validatePropertyForm(form) {
  const next = {};
  const location = String(form.location ?? "").trim();
  const totalSqft = Number(form.total_sqft);
  const bhk = Number(form.bhk);
  const bath = Number(form.bath);
  const balcony = Number(form.balcony);

  if (!location) next.location = "Enter a Bengaluru locality.";
  if (!form.area_type) next.area_type = "Select an area type.";
  if (!form.total_sqft || Number.isNaN(totalSqft) || totalSqft <= 0) {
    next.total_sqft = "Enter a total area greater than 0.";
  }
  if (!form.bhk || Number.isNaN(bhk) || bhk < 1 || !Number.isInteger(bhk)) {
    next.bhk = "BHK must be a whole number of at least 1.";
  }
  if (!form.bath || Number.isNaN(bath) || bath < 1) {
    next.bath = "Bathrooms must be at least 1.";
  }
  if (form.balcony === "" || Number.isNaN(balcony) || balcony < 0) {
    next.balcony = "Balcony count must be 0 or greater.";
  }

  return { valid: Object.keys(next).length === 0, errors: next };
}

/**
 * @param {Record<string, unknown>} form
 */
export function buildPredictPayload(form) {
  return {
    area_type: form.area_type,
    location: String(form.location).trim(),
    total_sqft: Number(form.total_sqft),
    bhk: Number.parseInt(String(form.bhk), 10),
    bath: Number(form.bath),
    balcony: Number(form.balcony),
    is_ready_to_move: Boolean(form.is_ready_to_move),
  };
}
