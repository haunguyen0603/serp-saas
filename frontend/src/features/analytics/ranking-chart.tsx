import type { KeywordRankingHistory } from "./types";

const WIDTH = 700;
const HEIGHT = 250;
const LEFT = 42;
const RIGHT = 18;
const TOP = 20;
const BOTTOM = 42;

export function RankingChart({ history }: { history: KeywordRankingHistory }) {
  const { points } = history;
  if (!points.length)
    return <p className="text-secondary">No ranking data in this range.</p>;
  const depth = Math.max(...points.map((point) => point.checked_depth), 10);
  const x = (index: number) =>
    LEFT + (index * (WIDTH - LEFT - RIGHT)) / Math.max(points.length - 1, 1);
  const y = (position: number) =>
    TOP + ((position - 1) * (HEIGHT - TOP - BOTTOM)) / Math.max(depth - 1, 1);
  const segments: string[][] = [];
  let segment: string[] = [];
  points.forEach((point, index) => {
    if (point.position === null) {
      if (segment.length) segments.push(segment);
      segment = [];
    } else segment.push(`${x(index)},${y(point.position)}`);
  });
  if (segment.length) segments.push(segment);
  return (
    <div className="ranking-chart">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Ranking positions for ${history.keyword} on ${history.tracked_site.name}; position 1 is at the top`}
      >
        {[1, Math.ceil(depth / 2), depth].map((position) => (
          <g key={position}>
            <line
              x1={LEFT}
              x2={WIDTH - RIGHT}
              y1={y(position)}
              y2={y(position)}
              className="ranking-chart-grid"
            />
            <text x={4} y={y(position) + 4} className="ranking-chart-label">
              #{position}
            </text>
          </g>
        ))}
        {segments.map((value, index) => (
          <polyline
            key={index}
            points={value.join(" ")}
            className="ranking-chart-line"
          />
        ))}
        {points.map((point, index) => {
          const label = `${new Date(point.checked_at).toLocaleString()}: ${
            point.position === null
              ? `Not found in Top ${point.checked_depth}`
              : `Position ${point.position}`
          }, ${history.tracked_site.name}`;
          return point.position === null ? (
            <g key={point.rank_check_id} aria-label={label}>
              <title>{label}</title>
              <path
                d={`M${x(index) - 4},${HEIGHT - BOTTOM - 4} l8,8 m0,-8 l-8,8`}
                className="ranking-chart-missing"
              />
            </g>
          ) : (
            <circle
              key={point.rank_check_id}
              cx={x(index)}
              cy={y(point.position)}
              r="5"
              className="ranking-chart-point"
              aria-label={label}
            >
              <title>{label}</title>
            </circle>
          );
        })}
        <text x={LEFT} y={HEIGHT - 10} className="ranking-chart-label">
          {new Date(points[0].checked_at).toLocaleDateString()}
        </text>
        {points.length > 1 && (
          <text
            x={WIDTH - RIGHT}
            y={HEIGHT - 10}
            textAnchor="end"
            className="ranking-chart-label"
          >
            {new Date(points.at(-1)!.checked_at).toLocaleDateString()}
          </text>
        )}
      </svg>
      <ul className="sr-only">
        {points.map((point) => (
          <li key={point.rank_check_id}>
            {new Date(point.checked_at).toLocaleString()}:{" "}
            {history.tracked_site.name},{" "}
            {point.position === null
              ? `not found in Top ${point.checked_depth}`
              : `position ${point.position}`}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-sm text-secondary">
        Solid circles are ranked observations. × means not found within the
        checked depth. Missing dates are not interpolated.
      </p>
    </div>
  );
}
