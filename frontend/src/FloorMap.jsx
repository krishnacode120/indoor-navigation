const sx = x => 62 + x * 36;
const sy = y => 52 + y * 34;

export default function FloorMap({ map, floor, route, position, destination, trail }) {
  const nodes = Object.fromEntries(map.nodes.map(n => [n.id, n]));
  const segments = (route?.coordinates || []).slice(1).map((b, i) => [route.coordinates[i], b]);
  const first = route?.coordinates[0];
  return <svg className="floor-map" viewBox="0 0 780 510" role="img" aria-label={`Floor ${floor} navigation map`}>
    <title>Floor {floor}, route and estimated position</title>
    <rect x="35" y="25" width="704" height="465" rx="6" fill="#f8fafb" stroke="#b9c8cb" strokeWidth="2" />
    {map.edges.map(({start, end}) => {
      const a = nodes[start], b = nodes[end];
      return a.floor === floor && b.floor === floor && <line key={`${start}-${end}`} x1={sx(a.x)} y1={sy(a.y)} x2={sx(b.x)} y2={sy(b.y)} stroke="#e1e8eb" strokeWidth="22" />;
    })}
    {trail.filter(p => p.floor === floor).map((p, i) => <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r="7" fill="#168879" opacity="0.16" />)}
    {segments.map(([a, b], i) => a.floor === floor && b.floor === floor && <line key={i} x1={sx(a.x)} y1={sy(a.y)} x2={sx(b.x)} y2={sy(b.y)} stroke="#167cbb" strokeWidth="6" strokeLinecap="round" />)}
    {position?.floor === floor && first?.floor === floor && <line x1={sx(position.x)} y1={sy(position.y)} x2={sx(first.x)} y2={sy(first.y)} stroke="#167cbb" strokeWidth="3" strokeDasharray="5 4" />}
    {map.nodes.filter(n => n.floor === floor).map(n => <g key={n.id}>
      <circle cx={sx(n.x)} cy={sy(n.y)} r={n.id === destination ? 10 : 5} fill={n.id === destination ? "#d45468" : n.stairs ? "#ac7b19" : "#8c9da5"} stroke="white" strokeWidth="2" />
      <text x={sx(n.x)} y={sy(n.y) + 23} textAnchor="middle" fontSize="11" fill="#52656c">{n.id.slice(3)}</text>
      {n.stairs && <text x={sx(n.x)} y={sy(n.y) - 14} textAnchor="middle" fontSize="11" fill="#866013">Stairs</text>}
    </g>)}
    {position?.floor === floor && <g>
      <circle cx={sx(position.x)} cy={sy(position.y)} r="16" fill="#0c8673" opacity="0.18" />
      <circle cx={sx(position.x)} cy={sy(position.y)} r="7" fill="#0c8673" stroke="white" strokeWidth="3" />
    </g>}
    <text x="62" y="492" fontSize="11" fill="#62737b">18 x 12 m</text>
  </svg>;
}
