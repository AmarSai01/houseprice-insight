import { useEffect, useMemo, useState } from "react";
import heroProperty from "../assets/hero-property.jpg";

/**
 * Single global architectural background for the entire website.
 * Same image + same cinematic dark overlay everywhere.
 *
 * motion=true  — extremely subtle drift/parallax (internal pages)
 * motion=false — static (Login / Register)
 */
const CinematicBackground = ({
  className = "",
  fixed = true,
  motion = true,
}) => {
  const [reduceMotion, setReduceMotion] = useState(false);
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const allowMotion = motion && !reduceMotion;

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduceMotion(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    if (!allowMotion) return undefined;

    const onMove = (event) => {
      if (window.innerWidth < 768) return;
      const x = (event.clientX / window.innerWidth - 0.5) * 2;
      const y = (event.clientY / window.innerHeight - 0.5) * 2;
      setPointer({
        x: Math.max(-1, Math.min(1, x)),
        y: Math.max(-1, Math.min(1, y)),
      });
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [allowMotion]);

  const imageTransform = useMemo(() => {
    if (!allowMotion) {
      return "translate3d(0,0,0) scale(1.06)";
    }
    const px = pointer.x * 5;
    const py = pointer.y * 3.5;
    return `translate3d(${px}px, ${py}px, 0) scale(1.06)`;
  }, [allowMotion, pointer]);

  return (
    <div
      aria-hidden="true"
      className={[
        fixed ? "fixed" : "absolute",
        "inset-0 z-0 overflow-hidden pointer-events-none",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      style={{ backgroundColor: "#0d121b" }}
    >
      {/* Same architectural image site-wide */}
      <div
        className="absolute inset-[-6%] will-change-transform"
        style={{
          transform: imageTransform,
          transition: allowMotion
            ? "transform 800ms cubic-bezier(0.22, 1, 0.36, 1)"
            : "none",
        }}
      >
        <div
          className={[
            "absolute inset-0 bg-cover bg-position-[center_42%]",
            allowMotion ? "hpi-cinematic-drift" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          style={{
            backgroundImage: `url(${heroProperty})`,
            opacity: 0.88,
            filter: "saturate(1.06) contrast(1.1)",
          }}
        />
      </div>

      {/* One consistent cinematic dark overlay — keeps architecture readable */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            linear-gradient(
              180deg,
              rgba(10, 14, 22, 0.42) 0%,
              rgba(13, 18, 27, 0.28) 35%,
              rgba(13, 18, 27, 0.34) 70%,
              rgba(8, 11, 18, 0.55) 100%
            ),
            linear-gradient(
              90deg,
              rgba(10, 14, 22, 0.32) 0%,
              transparent 26%,
              transparent 74%,
              rgba(10, 14, 22, 0.32) 100%
            ),
            radial-gradient(
              circle at 18% 16%,
              rgba(47, 125, 108, 0.10),
              transparent 34%
            )
          `,
        }}
      />
    </div>
  );
};

export default CinematicBackground;
