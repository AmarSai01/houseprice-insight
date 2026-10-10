/**
 * Reusable property input fields for Estimate-style flows.
 */

import {
  AREA_TYPE_OPTIONS,
} from "../services/propertyForm";

/**
 * @param {{
 *   idPrefix: string,
 *   form: Record<string, unknown>,
 *   errors: Record<string, string>,
 *   onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void,
 *   onToggleReady?: () => void,
 *   inputClass: (name: string) => string,
 *   fieldProps: (name: string) => Record<string, unknown>,
 * }} props
 */
export default function PropertyFormFields({
  idPrefix,
  form,
  errors,
  onChange,
  onToggleReady,
  inputClass,
  fieldProps,
}) {
  const fieldId = (name) => `${idPrefix}-${name}`;
  const errorId = (name) => `${idPrefix}-${name}-error`;

  return (
    <>
      <div className="hpi-est-field">
        <label htmlFor={fieldId("location")} className="hpi-est-label">
          Location
        </label>
        <input
          id={fieldId("location")}
          name="location"
          type="text"
          value={form.location}
          onChange={onChange}
          placeholder="e.g. Whitefield, Indiranagar, Yelahanka"
          className={inputClass("location")}
          autoComplete="off"
          {...fieldProps("location")}
          aria-describedby={errors.location ? errorId("location") : undefined}
        />
        {errors.location && (
          <p id={errorId("location")} className="hpi-est-field-error" role="alert">
            {errors.location}
          </p>
        )}
      </div>

      <div className="hpi-est-field-row">
        <div className="hpi-est-field">
          <label htmlFor={fieldId("area_type")} className="hpi-est-label">
            Area type
          </label>
          <select
            id={fieldId("area_type")}
            name="area_type"
            value={form.area_type}
            onChange={onChange}
            className={`hpi-est-select${errors.area_type ? " is-invalid" : ""}`}
            {...fieldProps("area_type")}
          >
            {AREA_TYPE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option.replace(/\s+/g, " ").trim()}
              </option>
            ))}
          </select>
          {errors.area_type && (
            <p id={errorId("area_type")} className="hpi-est-field-error" role="alert">
              {errors.area_type}
            </p>
          )}
        </div>

        <div className="hpi-est-field">
          <label htmlFor={fieldId("total_sqft")} className="hpi-est-label">
            Total area
          </label>
          <div className="hpi-est-unit">
            <input
              id={fieldId("total_sqft")}
              name="total_sqft"
              type="number"
              min="1"
              step="1"
              value={form.total_sqft}
              onChange={onChange}
              placeholder="1200"
              className={inputClass("total_sqft")}
              {...fieldProps("total_sqft")}
            />
            <span className="hpi-est-unit-tag">sq ft</span>
          </div>
          {errors.total_sqft && (
            <p id={errorId("total_sqft")} className="hpi-est-field-error" role="alert">
              {errors.total_sqft}
            </p>
          )}
        </div>
      </div>

      <div className="hpi-est-field-row">
        <div className="hpi-est-field">
          <label htmlFor={fieldId("bhk")} className="hpi-est-label">
            BHK
          </label>
          <input
            id={fieldId("bhk")}
            name="bhk"
            type="number"
            min="1"
            step="1"
            value={form.bhk}
            onChange={onChange}
            placeholder="2"
            className={inputClass("bhk")}
            {...fieldProps("bhk")}
          />
          {errors.bhk && (
            <p id={errorId("bhk")} className="hpi-est-field-error" role="alert">
              {errors.bhk}
            </p>
          )}
        </div>

        <div className="hpi-est-field">
          <label htmlFor={fieldId("bath")} className="hpi-est-label">
            Bathrooms
          </label>
          <input
            id={fieldId("bath")}
            name="bath"
            type="number"
            min="1"
            step="1"
            value={form.bath}
            onChange={onChange}
            placeholder="2"
            className={inputClass("bath")}
            {...fieldProps("bath")}
          />
          {errors.bath && (
            <p id={errorId("bath")} className="hpi-est-field-error" role="alert">
              {errors.bath}
            </p>
          )}
        </div>
      </div>

      <div className="hpi-est-field-row">
        <div className="hpi-est-field">
          <label htmlFor={fieldId("balcony")} className="hpi-est-label">
            Balcony count
          </label>
          <input
            id={fieldId("balcony")}
            name="balcony"
            type="number"
            min="0"
            step="1"
            value={form.balcony}
            onChange={onChange}
            placeholder="1"
            className={inputClass("balcony")}
            {...fieldProps("balcony")}
          />
          {errors.balcony && (
            <p id={errorId("balcony")} className="hpi-est-field-error" role="alert">
              {errors.balcony}
            </p>
          )}
        </div>

        <div className="hpi-est-field">
          <div className="hpi-est-switch-row">
            <div className="hpi-est-switch-copy">
              <p className="hpi-est-label">Ready to move</p>
              <p>
                {form.is_ready_to_move ? "Immediate possession" : "Not ready"}
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={Boolean(form.is_ready_to_move)}
              aria-label="Ready to move"
              className={`hpi-est-switch${
                form.is_ready_to_move ? " is-on" : ""
              }`}
              onClick={onToggleReady}
            >
              <span className="hpi-est-switch-knob" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
