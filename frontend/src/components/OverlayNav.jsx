import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Building2, Menu, X } from "lucide-react";

const LINKS = [
  { to: "/", label: "Home" },
  { to: "/estimate", label: "Estimate" },
  { to: "/market", label: "Market" },
  { to: "/how-it-works", label: "About" },
  { to: "/history", label: "History" },
];

/**
 * Transparent floating overlay navigation for the cinematic real-estate layout.
 */
const OverlayNav = ({ active = "" }) => {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="hpi-overlay-nav">
      <div className="mx-auto flex h-17 max-w-7xl items-center justify-between gap-4 px-5 sm:px-8 lg:px-10">
        <Link to="/" className="relative z-10 flex shrink-0 items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#173f3a] text-white">
            <Building2 size={16} strokeWidth={2} />
          </div>
          <div>
            <div className="text-[14px] font-semibold tracking-tight text-white">
              HousePrice
            </div>
            <div className="-mt-0.5 text-[10px] font-medium tracking-[0.18em] text-[#9dccbf]">
              INSIGHT
            </div>
          </div>
        </Link>

        <nav className="hpi-nav-pill absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 items-center gap-0.5 md:flex">
          {LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={
                active === link.to || (active === "home" && link.to === "/")
                  ? "hpi-nav-link-active"
                  : "hpi-nav-link"
              }
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="relative z-10 hidden items-center gap-2 md:flex">
          <Link to="/login" className="hpi-nav-signin">
            Sign In
          </Link>
          <Link to="/estimate" className="hpi-nav-cta">
            Estimate Price
            <ArrowRight size={14} />
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          className="hpi-nav-mobile-btn relative z-10"
          aria-label="Toggle navigation"
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {mobileOpen && (
        <div className="hpi-nav-mobile-panel">
          <nav className="flex flex-col gap-1">
            {LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileOpen(false)}
                className={
                  active === link.to || (active === "home" && link.to === "/")
                    ? "hpi-nav-mobile-link-active"
                    : "hpi-nav-mobile-link"
                }
              >
                {link.label}
              </Link>
            ))}
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
  );
};

export default OverlayNav;
