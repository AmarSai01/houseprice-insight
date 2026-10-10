import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Building2,
  Calendar,
  History as HistoryIcon,
  Loader2,
  LogIn,
  MapPin,
  Menu,
  X,
} from "lucide-react";
import api from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import CinematicBackground from "../components/CinematicBackground";

const formatLakhs = (value) =>
  Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const formatDate = (iso) => {
  if (!iso) return "Date unavailable";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const readFeature = (features, keys, fallback = "—") => {
  if (!features || typeof features !== "object") return fallback;
  for (const key of keys) {
    const value = features[key];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return fallback;
};

const UserDashboard = () => {
  const { isAuthenticated, loading: authLoading, user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const loadHistory = async () => {
      if (authLoading) return;

      if (!isAuthenticated) {
        setHistory([]);
        setHistoryLoading(false);
        setError("");
        return;
      }

      setHistoryLoading(true);
      setError("");
      try {
        const response = await api.get("/api/predict/history");
        if (!active) return;
        setHistory(Array.isArray(response.data) ? response.data : []);
      } catch (err) {
        if (!active) return;
        const detail = err?.response?.data?.detail;
        setHistory([]);
        setError(
          typeof detail === "string" && !detail.toLowerCase().includes("traceback")
            ? detail
            : "Unable to load your saved estimates right now. Please try again."
        );
      } finally {
        if (active) setHistoryLoading(false);
      }
    };

    loadHistory();
    return () => {
      active = false;
    };
  }, [authLoading, isAuthenticated]);

  return (
    <div className="relative min-h-screen overflow-x-hidden text-white">
      <CinematicBackground />
      <header className="hpi-nav relative">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-10">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#173f3a] text-white shadow-sm">
              <Building2 size={18} strokeWidth={2} />
            </div>
            <div>
              <div className="hpi-nav-brand">
                HousePrice
              </div>
              <div className="hpi-nav-brand-sub">
                INSIGHT
              </div>
            </div>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            <Link
              to="/"
              className="hpi-nav-link"
            >
              Home
            </Link>
            <Link
              to="/estimate"
              className="hpi-nav-link"
            >
              Estimate
            </Link>
            <Link
              to="/market"
              className="hpi-nav-link"
            >
              Market
            </Link>
            <Link
              to="/how-it-works"
              className="hpi-nav-link"
            >
              About
            </Link>
            <Link
              to="/history"
              className="hpi-nav-link-active"
            >
              History
            </Link>
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            <Link
              to="/login"
              className="hpi-nav-signin"
            >
              Sign In
            </Link>
            <Link
              to="/estimate"
              className="hpi-nav-cta"
            >
              Estimate Price
              <ArrowRight size={15} />
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setMobileOpen((open) => !open)}
            className="hpi-nav-mobile-btn"
            aria-label="Toggle navigation"
          >
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {mobileOpen && (
          <div className="hpi-nav-mobile-panel">
            <nav className="flex flex-col gap-1">
              <Link
                to="/"
                onClick={() => setMobileOpen(false)}
                className="hpi-nav-mobile-link"
              >
                Home
              </Link>
              <Link
                to="/estimate"
                onClick={() => setMobileOpen(false)}
                className="hpi-nav-mobile-link"
              >
                Estimate
              </Link>
              <Link
                to="/market"
                onClick={() => setMobileOpen(false)}
                className="hpi-nav-mobile-link"
              >
                Market
              </Link>
              <Link
                to="/how-it-works"
                onClick={() => setMobileOpen(false)}
                className="hpi-nav-mobile-link"
              >
                About
              </Link>
              <Link
                to="/history"
                onClick={() => setMobileOpen(false)}
                className="hpi-nav-mobile-link-active"
              >
                History
              </Link>
              <div className="mt-2 border-t border-white/10 pt-3">
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="hpi-nav-mobile-signin"
                >
                  Sign In
                </Link>
              </div>
            </nav>
          </div>
        )}
      </header>

      <main className="relative z-10 overflow-hidden">
        <div className="relative mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14 lg:px-10">
          <div className="mb-8 max-w-2xl">
            <div className="hpi-chip mb-5">
              <HistoryIcon size={14} />
              Saved estimates
            </div>
            <h1 className="hpi-page-title">
              Your prediction history
            </h1>
            <p className="hpi-page-lead">
              Review Bengaluru property estimates you have saved while signed
              in.
            </p>
          </div>

          {authLoading ? (
            <div className="flex min-h-[200px] items-center justify-center hpi-float-wide">
              <div className="flex items-center gap-2 text-sm text-white/55">
                <Loader2 size={18} className="animate-spin text-[#2f7d6c]" />
                Checking your account...
              </div>
            </div>
          ) : !isAuthenticated ? (
            <section className="hpi-float-wide px-6 py-12 text-center sm:px-10">
              <div className="mx-auto hpi-icon-well h-10 w-10">
                <LogIn size={18} />
              </div>
              <h2 className="mt-5 text-xl font-semibold text-white">
                Sign in to view saved estimates
              </h2>
              <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-white/70">
                Saved estimates are available after signing in. Guests can still
                create estimates on the Estimate page without creating an
                account.
              </p>
              <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Link
                  to="/login"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#173f3a] px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-[#24574f]"
                >
                  Sign In
                  <ArrowRight size={16} />
                </Link>
                <Link
                  to="/estimate"
                  className="hpi-btn-ghost px-6 py-3.5"
                >
                  Estimate a Property
                </Link>
              </div>
            </section>
          ) : (
            <section>
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-white/70">
                  Signed in as{" "}
                  <span className="font-medium text-white">
                    {user?.name || user?.email || "member"}
                  </span>
                </p>
                <Link
                  to="/estimate"
                  className="inline-flex items-center gap-2 text-sm font-semibold text-[#2f7d6c] hover:underline"
                >
                  New estimate
                  <ArrowRight size={15} />
                </Link>
              </div>

              {historyLoading ? (
                <div className="flex min-h-[180px] items-center justify-center hpi-float-wide">
                  <div className="flex items-center gap-2 text-sm text-white/55">
                    <Loader2 size={18} className="animate-spin text-[#2f7d6c]" />
                    Loading your history...
                  </div>
                </div>
              ) : error ? (
                <div className="hpi-error">
                  {error}
                </div>
              ) : history.length === 0 ? (
                <div className="hpi-float-wide px-6 py-12 text-center">
                  <div className="mx-auto hpi-icon-well h-14 w-14 rounded-2xl">
                    <HistoryIcon size={24} />
                  </div>
                  <h2 className="mt-5 text-xl font-semibold text-white">
                    No saved estimates yet
                  </h2>
                  <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-white/70">
                    When you create an estimate while signed in, it will appear
                    here for easy reference.
                  </p>
                  <Link
                    to="/estimate"
                    className="mt-7 inline-flex items-center justify-center gap-2 rounded-xl bg-[#173f3a] px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-[#24574f]"
                  >
                    Estimate a Property
                    <ArrowRight size={16} />
                  </Link>
                </div>
              ) : (
                <ul className="space-y-4">
                  {history.map((item) => {
                    const features = item.input_features || {};
                    const location = readFeature(features, ["location"]);
                    const totalSqft = readFeature(features, [
                      "total_sqft",
                      "square_feet",
                    ]);
                    const bhk = readFeature(features, [
                      "bhk",
                      "number_of_bedrooms",
                    ]);
                    const bath = readFeature(features, [
                      "bath",
                      "number_of_bathrooms",
                    ]);
                    const low =
                      features.estimated_low_lakhs ?? item.estimated_low_lakhs;
                    const high =
                      features.estimated_high_lakhs ??
                      item.estimated_high_lakhs;
                    const hasRange =
                      low !== undefined &&
                      low !== null &&
                      high !== undefined &&
                      high !== null;

                    return (
                      <li
                        key={item.id}
                        className="hpi-float-wide"
                      >
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="flex items-center gap-2 text-[#2f7d6c]">
                              <MapPin size={16} />
                              <h2 className="text-lg font-semibold text-white">
                                {location}
                              </h2>
                            </div>
                            <p className="mt-2 flex items-center gap-2 text-xs text-white/55">
                              <Calendar size={13} />
                              {formatDate(item.timestamp)}
                            </p>
                          </div>
                          <div className="sm:text-right">
                            <p className="text-xs font-semibold uppercase tracking-wide text-white/55">
                              Estimated price
                            </p>
                            <p className="mt-1 text-2xl font-semibold tracking-tight text-white">
                              ₹{formatLakhs(item.predicted_value)}{" "}
                              <span className="text-base font-semibold text-[#2f7d6c]">
                                Lakh
                              </span>
                            </p>
                            {hasRange && (
                              <p className="mt-1 text-sm text-white/70">
                                Range ₹{formatLakhs(low)}L – ₹
                                {formatLakhs(high)}L
                              </p>
                            )}
                          </div>
                        </div>

                        <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-white/10 pt-4 text-sm sm:grid-cols-3">
                          <div>
                            <dt className="text-white/55">Total area</dt>
                            <dd className="mt-0.5 font-medium text-white">
                              {totalSqft === "—"
                                ? "—"
                                : `${Number(totalSqft).toLocaleString("en-IN")} sq ft`}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-white/55">BHK</dt>
                            <dd className="mt-0.5 font-medium text-white">
                              {bhk}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-white/55">Bathrooms</dt>
                            <dd className="mt-0.5 font-medium text-white">
                              {bath}
                            </dd>
                          </div>
                        </dl>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          )}
        </div>
      </main>
    </div>
  );
};

export default UserDashboard;
