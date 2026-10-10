/**
 * Lightweight SVG scatter for held-out predicted vs actual prices.
 * No chart library dependency.
 */

import { useMemo } from "react";
import { computeSharedAxisBounds } from "../services/modelEvaluation";

const WIDTH = 640;
const HEIGHT = 420;
const PAD = { top: 24, right: 20, bottom: 52, left: 64 };

function mapValue(value, min, max, start, end) {
  if (max === min) return (start + end) / 2;
  return start + ((value - min) / (max - min)) * (end - start);
}

/**
 * @param {{
 *   points: Array<{ actual_price_lakhs: number, predicted_price_lakhs: number }>,
 * }} props
 */
export default function PredictedVsActualChart({ points }) {
  const bounds = useMemo(() => computeSharedAxisBounds(points), [points]);

  const plotted = useMemo(() => {
    const { min, max } = bounds;
    const innerLeft = PAD.left;
    const innerRight = WIDTH - PAD.right;
    const innerTop = PAD.top;
    const innerBottom = HEIGHT - PAD.bottom;

    return points.map((point, index) => {
      const x = mapValue(
        point.actual_price_lakhs,
        min,
        max,
        innerLeft,
        innerRight
      );
      const y = mapValue(
        point.predicted_price_lakhs,
        min,
        max,
        innerBottom,
        innerTop
      );
      return { x, y, index };
    });
  }, [bounds, points]);

  const { min, max } = bounds;
  const x0 = PAD.left;
  const x1 = WIDTH - PAD.right;
  const y0 = HEIGHT - PAD.bottom;
  const y1 = PAD.top;
  const idealX1 = mapValue(max, min, max, x0, x1);
  const idealY1 = mapValue(max, min, max, y0, y1);
  const idealX0 = mapValue(min, min, max, x0, x1);
  const idealY0 = mapValue(min, min, max, y0, y1);

  const tickCount = 4;
  const ticks = Array.from({ length: tickCount + 1 }, (_, i) => {
    const t = min + ((max - min) * i) / tickCount;
    return {
      value: t,
      x: mapValue(t, min, max, x0, x1),
      y: mapValue(t, min, max, y0, y1),
    };
  });

  return (
    <svg
      className="hpi-about-scatter"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label="Scatter plot of predicted price versus actual price in INR lakhs on the held-out test set, with an ideal predicted equals actual reference line."
    >
      <title>Predicted vs actual prices (INR lakhs)</title>
      <desc>
        Each point is one held-out test property. The diagonal line shows where
        predicted price equals actual price.
      </desc>

      <rect
        x={x0}
        y={y1}
        width={x1 - x0}
        height={y0 - y1}
        className="hpi-about-scatter-frame"
      />

      {ticks.map((tick) => (
        <g key={`tick-${tick.value}`}>
          <line
            x1={tick.x}
            y1={y0}
            x2={tick.x}
            y2={y1}
            className="hpi-about-scatter-grid"
          />
          <line
            x1={x0}
            y1={tick.y}
            x2={x1}
            y2={tick.y}
            className="hpi-about-scatter-grid"
          />
          <text
            x={tick.x}
            y={y0 + 18}
            textAnchor="middle"
            className="hpi-about-scatter-tick"
          >
            {Math.round(tick.value).toLocaleString("en-IN")}
          </text>
          <text
            x={x0 - 10}
            y={tick.y + 4}
            textAnchor="end"
            className="hpi-about-scatter-tick"
          >
            {Math.round(tick.value).toLocaleString("en-IN")}
          </text>
        </g>
      ))}

      <line
        x1={idealX0}
        y1={idealY0}
        x2={idealX1}
        y2={idealY1}
        className="hpi-about-scatter-ideal"
      />
      <text
        x={idealX1 - 8}
        y={idealY1 + 14}
        textAnchor="end"
        className="hpi-about-scatter-ideal-label"
      >
        Ideal: predicted = actual
      </text>

      {plotted.map((point) => (
        <circle
          key={point.index}
          cx={point.x}
          cy={point.y}
          r={2.1}
          className="hpi-about-scatter-point"
        />
      ))}

      <text
        x={(x0 + x1) / 2}
        y={HEIGHT - 12}
        textAnchor="middle"
        className="hpi-about-scatter-axis"
      >
        Actual price (₹ lakhs)
      </text>
      <text
        x={18}
        y={(y0 + y1) / 2}
        textAnchor="middle"
        transform={`rotate(-90 18 ${(y0 + y1) / 2})`}
        className="hpi-about-scatter-axis"
      >
        Predicted price (₹ lakhs)
      </text>
    </svg>
  );
}
