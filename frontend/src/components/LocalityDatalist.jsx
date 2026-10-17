/**
 * Type-ahead suggestions for location inputs, limited to localities the model knows.
 */

import { MODEL_LOCALITIES } from "../constants/localities";
import { matchModelLocality } from "../services/propertyForm";

export const LOCALITY_DATALIST_ID = "hpi-model-localities";

export function getLocalityHint(value) {
  const query = String(value ?? "").trim().replace(/\s+/g, " ").toLowerCase();
  if (!query) {
    return `Start typing to choose from ${MODEL_LOCALITIES.length} Bengaluru localities the model knows.`;
  }
  const exact = matchModelLocality(value);
  if (exact) return `✓ ${exact} is a locality the model knows.`;
  const partial = MODEL_LOCALITIES.filter((name) => name.toLowerCase().includes(query)).length;
  if (partial) {
    return `${partial} matching ${partial === 1 ? "locality" : "localities"} — pick one from the suggestions.`;
  }
  return "The model doesn't know this locality by name, so it will be estimated as “Other” (less precise).";
}

export default function LocalityDatalist() {
  return (
    <datalist id={LOCALITY_DATALIST_ID}>
      {MODEL_LOCALITIES.map((name) => (
        <option key={name} value={name} />
      ))}
    </datalist>
  );
}
