/**
 * Convert Axios/API failures into user-facing messages.
 * Does not alter auth session handling — callers decide what to do with 401.
 */
export function getApiErrorMessage(
  error,
  fallback = "Something went wrong. Please try again."
) {
  if (!error) return fallback;

  if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
    return "Cannot connect to the server. Please confirm the backend is running.";
  }

  const status = error.response?.status;
  const data = error.response?.data;
  const detail = data?.detail;

  if (status === 422) {
    const errors = data?.errors;
    if (Array.isArray(errors) && errors.length > 0) {
      const first = errors[0];
      const field = first.field
        ? String(first.field).replace(/^body\./, "")
        : "";
      const message = String(first.message || "Invalid value").replace(
        /^Value error, /i,
        ""
      );
      return field
        ? `Please check ${field}: ${message}`
        : "Please check your input and try again.";
    }
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) {
      return String(detail[0].msg);
    }
    return "Some details are invalid. Please review and try again.";
  }

  if (typeof detail === "string" && !detail.toLowerCase().includes("traceback")) {
    return detail;
  }

  if (Array.isArray(detail) && detail[0]?.msg) {
    return String(detail[0].msg);
  }

  switch (status) {
    case 400:
      return fallback;
    case 401:
      return "Please sign in again to continue.";
    case 403:
      return "You do not have permission to perform this action.";
    case 404:
      return "The requested resource was not found.";
    case 429:
      return "Too many requests. Please wait a moment and try again.";
    case 503:
      return "The service is temporarily unavailable. Please try again shortly.";
    case 500:
    case 502:
    case 504:
      return "A server error occurred. Please try again.";
    default:
      return fallback;
  }
}
