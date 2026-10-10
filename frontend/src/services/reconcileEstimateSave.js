/**
 * After an authenticated estimate returns saved=false, decide whether the
 * session expired or the save failed for another reason.
 *
 * Guest callers must pass wasAuthenticated=false so /api/auth/me is never called.
 */
export async function reconcileUnauthenticatedSave({
  wasAuthenticated,
  saved,
  verifySession,
  clearSession,
}) {
  if (!wasAuthenticated || saved === true) {
    return { status: "ok" };
  }

  try {
    await verifySession();
    return { status: "save_failed" };
  } catch (error) {
    const status = error?.response?.status;
    if (status === 401) {
      clearSession();
      return { status: "session_expired" };
    }
    // Could not confirm an invalid JWT (e.g. network). Keep the session.
    return { status: "save_failed" };
  }
}

export const SESSION_EXPIRED_SAVE_MESSAGE =
  "Your session expired. Please sign in again to save this estimate.";
