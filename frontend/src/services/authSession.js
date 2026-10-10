/**
 * Bridge between axios (api.js) and AuthContext without circular imports.
 * AuthProvider registers a handler; api.js notifies on auth session invalidation.
 */

let invalidSessionHandler = null;

export function registerInvalidSessionHandler(handler) {
  invalidSessionHandler = typeof handler === "function" ? handler : null;
  return () => {
    if (invalidSessionHandler === handler) {
      invalidSessionHandler = null;
    }
  };
}

export function notifyInvalidSession() {
  if (typeof invalidSessionHandler === "function") {
    invalidSessionHandler();
  }
}

export function clearAuthStorage() {
  localStorage.removeItem("token");
}
