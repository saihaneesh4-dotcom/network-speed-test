import { useState } from 'react'
import './App.css'

const initialServers = [
  { id: 'server_01', name: 'Server A', host: '10.56.66.133:5001', status: 'Online', latency: '10.6 ms' },
  { id: 'server_02', name: 'Server B', host: '10.140.251.133:5002', status: 'Offline', latency: '—' },
  { id: 'server_03', name: 'Server C', host: '10.140.251.133:5003', status: 'Offline', latency: '—' },
]

const history = [
  { id: 6, server: 'Server A', download: 95.4, upload: 42.8, latency: 12.5, time: '19:54:51' },
  { id: 5, server: 'Server B', download: 100, upload: 45, latency: 0.317, time: '23:49:01' },
  { id: 4, server: 'Server C', download: 100, upload: 45, latency: 0.316, time: '23:45:53' },
  { id: 3, server: 'Server C', download: 105.7, upload: 50.1, latency: 10.8, time: '23:16:55' },
  { id: 2, server: 'Server A', download: 102.4, upload: 48.6, latency: 11.7, time: '23:05:00' },
]

const navigation = [
  { label: 'Dashboard', icon: '◫', sub: 'Overview & insights' },
  { label: 'Network Visualiser', icon: '⌘', sub: 'Live topology & traffic' },
  { label: 'Query Intelligence', icon: '▤', sub: 'Subqueries & execution' },
  { label: 'Cost Analytics', icon: '◇', sub: 'Query costs & savings' },
  { label: 'System Health', icon: '⬡', sub: 'Infrastructure metrics' },
]

function MetricCard({ icon, label, value, unit, tone, foot }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon ${tone}`}>{icon}</div>
      <div className="metric-copy">
        <span>{label}</span>
        <strong>{value}<small>{unit}</small></strong>
        <em>{foot}</em>
      </div>
    </article>
  )
}

function LineChart({ type = 'download' }) {
  const download = [30, 34, 32, 39, 36, 42, 38, 44, 40, 48, 43, 46, 39, 51, 44, 47, 43, 49, 45, 53, 47, 50, 44, 48]
  const upload = [14, 16, 15, 18, 17, 19, 16, 21, 18, 20, 17, 22, 19, 21, 18, 23, 20, 22, 19, 24, 21, 23, 20, 22]
  const points = (values) => values.map((value, i) => `${i * 20},${110 - value * 1.7}`).join(' ')
  const values = type === 'upload' ? upload : download

  return (
    <svg className="line-chart" viewBox="0 0 460 125" preserveAspectRatio="none" role="img" aria-label={`${type} trend chart`}>
      {[20, 45, 70, 95].map(y => <line key={y} x1="0" y1={y} x2="460" y2={y} className="chart-grid" />)}
      <polygon points={`0,125 ${points(values)} 460,125`} className={`chart-area ${type}`} />
      <polyline points={points(values)} className={`chart-line ${type}`} />
      {type === 'download' && <polyline points={points(upload)} className="chart-line upload overlay" />}
    </svg>
  )
}

function App() {
  const [activePage, setActivePage] = useState('Network Visualiser')
  const [period, setPeriod] = useState('Last hour')
  const [query, setQuery] = useState('')
  const [isLive, setIsLive] = useState(true)

  const visibleHistory = history.filter(item =>
    `${item.server} ${item.id}`.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">∿</div>
          <div><strong>SpeedTest <span>Network</span></strong><small>Distributed Network Analytics</small></div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <nav className="navigation">
          {navigation.map(item => (
            <button key={item.label} className={`nav-item ${activePage === item.label ? 'active' : ''}`} onClick={() => setActivePage(item.label)}>
              <span className="nav-icon">{item.icon}</span>
              <span><strong>{item.label}</strong><small>{item.sub}</small></span>
              {activePage === item.label && <span className="nav-active-dot" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-label"><span className="pulse-dot" /> SYSTEM STATUS</div>
          <div className="health-row"><span className="status-dot green" /> Flask API <span>Reachable</span></div>
          <div className="health-row"><span className="status-dot green" /> Server A <span>Probed</span></div>
          <div className="health-row"><span className="status-dot red" /> Server B/C <span>Unverified</span></div>
          <div className="sidebar-footer">NETWORK SPEED-TEST PLATFORM<br />Development environment</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> <strong>{activePage}</strong></div>
          <label className="search-box"><span>⌕</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search servers or test history..." /></label>
          <div className="top-status"><span className="pulse-dot" /><div><strong>API connected</strong><small>Local development</small></div></div>
          <div className="profile"><div className="avatar">H</div><div><strong>Haneesh</strong><small>Developer</small></div></div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div><div className="eyebrow"><span className="pulse-dot" /> NETWORK OPERATIONS CENTER</div><h1>{activePage}</h1><p>Monitor your federated network and analyze performance across measurement servers.</p></div>
            <button className={`live-button ${isLive ? 'selected' : ''}`} onClick={() => setIsLive(!isLive)}><span className="pulse-dot" /> {isLive ? 'LIVE VIEW' : 'PAUSED'}</button>
          </div>

          <section className="metrics-grid">
            <MetricCard icon="◈" label="Configured servers" value="3" unit="" tone="cyan" foot="1 probe verified" />
            <MetricCard icon="↓" label="Latest download" value="95.4" unit="Mbps" tone="blue" foot="From saved API result" />
            <MetricCard icon="↑" label="Latest upload" value="42.8" unit="Mbps" tone="purple" foot="From saved API result" />
            <MetricCard icon="ϟ" label="Latest latency" value="12.5" unit="ms" tone="amber" foot="Stored measurement" />
          </section>

          <section className="primary-grid">
            <article className="panel topology-panel">
              <div className="panel-heading"><div><span className="panel-kicker">FEDERATION MAP</span><h2>Network topology</h2><p>Measurement server connectivity</p></div><span className={`live-tag ${isLive ? '' : 'paused'}`}><span className="pulse-dot" />{isLive ? 'MONITORING' : 'PAUSED'}</span></div>

              <div className="topology-canvas">
                <div className="topology-glow" />
                <svg className="connection-lines" viewBox="0 0 700 370" preserveAspectRatio="none">
                  <defs><linearGradient id="flow" x1="0" y1="0" x2="1" y2="0"><stop stopColor="#0debd1" /><stop offset="1" stopColor="#4777ff" /></linearGradient></defs>
                  {[[160,180,470,70],[160,180,470,185],[160,180,470,300]].map((line, i) => <g key={i}><path d={`M ${line[0]} ${line[1]} C 280 ${line[1]}, 340 ${line[3]}, ${line[2]} ${line[3]}`} className={`connection ${i === 0 ? 'connection-active' : ''}`} /><circle r="4" className={i === 0 ? 'flow-dot' : 'idle-dot'}><animateMotion dur={`${2.5 + i}s`} repeatCount="indefinite" path={`M ${line[0]} ${line[1]} C 280 ${line[1]}, 340 ${line[3]}, ${line[2]} ${line[3]}`} /></circle></g>)}
                </svg>

                <div className="node client-node"><div className="node-orb">⌘</div><strong>Your client</strong><small>HP · Windows</small></div>
                {initialServers.map((server, i) => <div key={server.id} className={`node server-node server-${i + 1}`}><div className={`node-orb ${server.status === 'Online' ? 'online' : 'offline'}`}>▤</div><div className="node-copy"><strong>{server.name}</strong><small>{server.host}</small><span className={server.status === 'Online' ? 'online-text' : 'offline-text'}><i />{server.status} · {server.latency}</span></div></div>)}
                <div className="topology-legend"><span><i className="legend-line active-line" /> Verified probe</span><span><i className="legend-line idle-line" /> Unverified connection</span><span><i className="legend-dot" /> Data-flow animation (visual demo)</span></div>
              </div>
            </article>

            <article className="panel performance-panel">
              <div className="panel-heading"><div><span className="panel-kicker">PERFORMANCE TELEMETRY</span><h2>Throughput overview</h2><p>Historical records · not a live stream</p></div><select value={period} onChange={e => setPeriod(e.target.value)}><option>Last hour</option><option>24 hours</option><option>7 days</option></select></div>
              <div className="chart-stats"><div><span className="chart-legend cyan-legend" />Download<strong>95.4 <small>Mbps</small></strong></div><div><span className="chart-legend purple-legend" />Upload<strong>42.8 <small>Mbps</small></strong></div></div>
              <div className="chart-wrap"><div className="chart-ylabels"><span>120</span><span>90</span><span>60</span><span>30</span><span>0</span></div><LineChart /></div>
              <div className="chart-xlabels"><span>Earlier</span><span>Recent</span><span>Latest saved result</span></div>
              <div className="chart-note"><span className="status-dot green" />Showing illustrative trend shapes; historical API records will replace them next.</div>
            </article>
          </section>

          <section className="bottom-grid">
            <article className="panel history-panel">
              <div className="panel-heading"><div><span className="panel-kicker">MEASUREMENT LOG</span><h2>Recent speed tests</h2><p>Saved records from the backend response</p></div><span className="count-tag">{visibleHistory.length} records</span></div>
              <div className="table-scroll"><table><thead><tr><th>ID</th><th>Server</th><th>Download</th><th>Upload</th><th>Latency</th><th>Time</th></tr></thead><tbody>{visibleHistory.map(row => <tr key={row.id}><td className="muted-cell">#{row.id}</td><td><span className="table-server-dot" />{row.server}</td><td className="cyan-cell">{row.download} Mbps</td><td className="purple-cell">{row.upload} Mbps</td><td>{row.latency} ms</td><td>{row.time}</td></tr>)}</tbody></table></div>
              <div className="table-foot">Sample of the six records retrieved from Santosh's API · static preview</div>
            </article>

            <article className="panel server-panel"><div className="panel-heading"><div><span className="panel-kicker">SERVER FEDERATION</span><h2>Probe results</h2><p>Last confirmed application probe</p></div></div><div className="server-result"><div className="result-icon">A</div><div className="result-copy"><strong>Server A</strong><small>10.56.66.133:5001</small><span>Probe response received</span></div><strong className="result-ms">10.62 <small>ms</small></strong></div><div className="server-result muted-result"><div className="result-icon">B</div><div className="result-copy"><strong>Server B</strong><small>Configured endpoint</small><span>Availability not confirmed</span></div><strong className="result-ms">—</strong></div><div className="server-result muted-result"><div className="result-icon">C</div><div className="result-copy"><strong>Server C</strong><small>Configured endpoint</small><span>Availability not confirmed</span></div><strong className="result-ms">—</strong></div><div className="server-note">Probe latency is application-level RTT, not an Internet speed measurement.</div></article>
          </section>

          <footer className="page-footer"><span>SpeedTest Network <b>·</b> Mini-Ookla federation project</span><span><i className="status-dot green" /> Dashboard UI preview <b>·</b> Real API integration pending</span></footer>
        </div>
      </main>
    </div>
  )
}

export default App