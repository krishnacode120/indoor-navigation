import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import FloorMap from "./FloorMap";

function WifiIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M2 8a16 16 0 0 1 20 0M5 12a11 11 0 0 1 14 0M9 16a5 5 0 0 1 6 0"/><circle cx="12" cy="20" r="1"/></svg>;
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState("");
  const [connecting, setConnecting] = useState(true);
  const [busy, setBusy] = useState(false);
  const [model, setModel] = useState("knn");
  const [floor, setFloor] = useState(1);
  const [source, setSource] = useState("F1_P01");
  const [destination, setDestination] = useState("F2_P20");
  const [position, setPosition] = useState(null);
  const [scan, setScan] = useState(null);
  const [route, setRoute] = useState(null);
  const [tracking, setTracking] = useState(false);
  const [smooth, setSmooth] = useState(true);
  const [heatmap, setHeatmap] = useState(false);
  const [trail, setTrail] = useState([]);
  const [mode, setMode] = useState("mock");
  const [manual, setManual] = useState("-45, -60, -70, -80, -55, -67, -73, -64");
  const history = useRef([]);
  const pending = useRef(false);

  const connect = useCallback(async () => {
    setConnecting(true); setError("");
    try { setMeta(await api("/metadata")); }
    catch (e) { setMeta(null); setError(e.message); }
    finally { setConnecting(false); }
  }, []);
  useEffect(() => { connect(); }, [connect]);

  // Clear temporal state when the simulated device or estimator changes.
  useEffect(() => {
    history.current = []; setPosition(null); setScan(null); setRoute(null); setTrail([]);
  }, [source, model, mode, smooth]);

  const locate = useCallback(async () => {
    if (pending.current || !meta) return;
    pending.current = true; setBusy(true); setError("");
    try {
      let input;
      if (mode === "mock") input = await api(`/scan/mock?node=${encodeURIComponent(source)}`);
      else {
        const values = manual.split(",").map(s => s.trim());
        const signals = values.map(v => v === "" || v === "null" ? null : Number(v));
        if (signals.some(v => v !== null && !Number.isFinite(v))) throw new Error("Enter comma-separated numbers; use null for missing APs.");
        input = {signals};
      }
      setScan(input);
      const prediction = await api("/predict", {signals: input.signals, model});
      if (smooth) {
        if (history.current.at(-1)?.floor !== prediction.floor) history.current = [];
        history.current = [...history.current.slice(-3), prediction];
        const samples = history.current;
        const x = samples.reduce((sum, p) => sum + p.x, 0) / samples.length;
        const y = samples.reduce((sum, p) => sum + p.y, 0) / samples.length;
        // Keep raw samples in history; smooth only the displayed estimate.
        const result = {...prediction, x: +x.toFixed(2), y: +y.toFixed(2)};
        setPosition(result); setTrail(t => [...t.slice(-119), result]);
      } else {
        setPosition(prediction); setTrail(t => [...t.slice(-119), prediction]);
      }
      setFloor(prediction.floor);
    } catch (e) { setError(e.message); setTracking(false); setPosition(null); setRoute(null); }
    finally { pending.current = false; setBusy(false); }
  }, [meta, source, mode, manual, model, smooth]);

  useEffect(() => {
    if (!tracking) return;
    const id = window.setInterval(locate, 2500);
    return () => window.clearInterval(id);
  }, [tracking, locate]);

  useEffect(() => {
    setRoute(null);
    if (!position) return;
    const controller = new AbortController();
    api("/route", {position: {x: position.x, y: position.y, floor: position.floor}, destination}, controller.signal)
      .then(setRoute).catch(e => { if (e.name !== "AbortError") setError(e.message); });
    return () => controller.abort();
  }, [position, destination]);

  const metrics = meta?.metrics;
  const nodes = meta?.map.nodes || [];
  const nodeOptions = nodes.map(n => <option key={n.id} value={n.id}>{n.label} ({n.id.slice(3)})</option>);
  const signals = scan ? meta.ap_names.map((ap, i) => Array.isArray(scan.signals) ? scan.signals[i] : scan.signals[ap]) : [];

  return <main>
    <header className="topbar">
      <div className="brand"><span className="brand-icon"><WifiIcon /></span><div><h1>Indoor Navigation</h1><p>North campus / Learning block</p></div></div>
      <div className="connection"><span className={meta ? "online" : "offline"} />{connecting ? "Connecting" : meta ? "System connected" : "Disconnected"}<button className="icon-button" title="Reconnect" aria-label="Reconnect" onClick={connect} disabled={connecting}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 6v6h-6M20 12a8 8 0 1 0-2 6"/></svg></button></div>
    </header>
    {error && <div className="error" role="alert">{error}</div>}
    <div className="workspace">
      <aside>
        <div className="section-heading"><h2>Locate & navigate</h2><span className="tag">{mode === "mock" ? "Simulation" : "Manual RSSI"}</span></div>
        <label>Signal source<select value={mode} onChange={e => setMode(e.target.value)} disabled={busy}><option value="mock">Simulated WiFi scan</option><option value="manual">Manual RSSI</option></select></label>
        {mode === "mock" ? <label>Simulated device location<select value={source} onChange={e => setSource(e.target.value)} disabled={busy || !meta}>{nodeOptions}</select></label> : <label>RSSI / AP1 to AP8<textarea value={manual} onChange={e => setManual(e.target.value)} disabled={busy} rows="3" /></label>}
        <label>Positioning model<select value={model} onChange={e => setModel(e.target.value)} disabled={busy}><option value="knn">K-nearest neighbors</option><option value="rf">Random forest</option></select></label>
        <button className="primary" disabled={!meta || busy} onClick={locate}><WifiIcon />{busy ? "Locating..." : "Scan WiFi & Locate"}</button>
        <div className="checks"><label><input type="checkbox" checked={tracking} disabled={!meta || busy} onChange={e => setTracking(e.target.checked)} />Continuous scans</label><label><input type="checkbox" checked={smooth} disabled={busy} onChange={e => setSmooth(e.target.checked)} />Smooth position</label></div>
        <div className="divider" />
        <label>Destination<select value={destination} onChange={e => setDestination(e.target.value)} disabled={!meta}>{nodeOptions}</select></label>
        <dl className="position"><div><dt>Estimated position</dt><dd>{position ? `${position.x.toFixed(2)}, ${position.y.toFixed(2)} m` : "Awaiting scan"}</dd></div><div><dt>Floor</dt><dd>{position?.floor || "--"}</dd></div><div><dt>Nearest waypoint</dt><dd>{route?.start || "--"}</dd></div></dl>
        {route && <div className="route-detail"><strong>{route.distance_m.toFixed(1)} m</strong><span>{route.path.length} waypoints</span>{route.transitions.map(t => <p key={t.at}>Stairs at {t.at.slice(3)} to floor {t.to_floor}</p>)}<details><summary>Route waypoints</summary><p>{route.path.join(" > ")}</p></details></div>}
      </aside>
      <section className="map-area">
        <div className="map-toolbar"><div><h2>Building overview</h2><p>Learning block / Floor {floor}</p></div><div className="segments">{[1,2].map(f => <button key={f} aria-pressed={floor === f} onClick={() => setFloor(f)} className={floor === f ? "active" : ""}>Floor {f}</button>)}</div></div>
        {meta ? <FloorMap map={meta.map} floor={floor} route={route} position={position} destination={destination} trail={heatmap ? trail : []} /> : <div className="empty-map">{connecting ? "Connecting to building map..." : "Building map unavailable"}<button onClick={connect} disabled={connecting}>Reconnect</button></div>}
        <div className="map-legend"><span><i className="you"/>Your estimate</span><span><i className="target"/>Destination</span><span><i className="path"/>Route</span><label><input type="checkbox" checked={heatmap} onChange={e => setHeatmap(e.target.checked)}/>Movement trail</label></div>
        <section className="signal-section"><div className="section-heading"><h2>Access point readings</h2><span>{signals.filter(s => s != null && s > -100).length} / {meta?.ap_names.length || 8} detected</span></div><div className="signals">{(meta?.ap_names || Array.from({length:8},(_,i)=>`AP${i+1}`)).map((ap,i) => <div className="signal" key={ap}><div><strong>{ap}</strong><span>{signals[i] == null || signals[i] <= -100 ? "--" : `${signals[i]} dBm`}</span></div><div className="meter"><i style={{width:`${signals[i] == null ? 0 : Math.max(0,Math.min(100,(signals[i]+100)/70*100))}%`}} /></div></div>)}</div></section>
      </section>
    </div>
    <footer><span className="footer-label">OFFLINE SURVEY</span><div><strong>{metrics?.locations ?? "--"}</strong><span>grid locations</span></div><div><strong>{metrics?.scans ?? "--"}</strong><span>fingerprints</span></div><div><strong>{metrics?.models.knn.mean_error_m ?? "--"} m</strong><span>KNN mean error</span></div><div><strong>{metrics?.models.rf.mean_error_m ?? "--"} m</strong><span>RF mean error</span></div><div><strong>{metrics ? `${(metrics.floor_accuracy*100).toFixed(1)}%` : "--"}</strong><span>floor accuracy</span></div><span className="evaluation">Synthetic data<br/>Held-out locations</span></footer>
  </main>;
}
