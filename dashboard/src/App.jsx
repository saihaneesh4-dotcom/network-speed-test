import { useEffect, useState } from 'react'
import './App.css'
import { sampleResults } from "./sampledata";

const initialServers = [
  { id: 'server_01', name: 'Server A', host: '10.149.250.133:5001', status: 'Unknown', latency: '—' },
  { id: 'server_02', name: 'Server B', host: '10.149.250.133:5002', status: 'Unknown', latency: '—' },
  { id: 'server_03', name: 'Server C', host: '10.149.250.133:5003', status: 'Unknown', latency: '—' },
]




const navigation = [
  {
    label: 'Validation Sessions',
    icon: '<>',
    sub: 'Compare linked Mini-Ookla & iperf3 tests',
  },
  {
    label: 'Network Visualiser',
    icon: '[]',
    sub: 'Latest test & network overview',
  },
  {
    label: 'Performance Comparison',
    icon: '<>',
    sub: 'Compare network measurements',
  },
  {
    label: 'iperf3 Performance',
    icon: '>>',
    sub: 'TCP throughput & measurement history',
  },
  {
    label: 'Measurement History',
    icon: '##',
    sub: 'Browse saved speed tests',
  },
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



function ThroughputComparisonChart({ title, history = [] }) {
  const width = 700
  const height = 250
  const left = 55
  const right = 18
  const top = 20
  const bottom = 48
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom

  const points = history.map((item, index) => ({
    ...item,
    index,
    mini: item.mini == null || item.mini === '' ? null : Number(item.mini),
    iperf: item.iperf == null || item.iperf === '' ? null : Number(item.iperf),
  })).filter(item =>
    (item.mini !== null && Number.isFinite(item.mini) && item.mini >= 0) ||
    (item.iperf !== null && Number.isFinite(item.iperf) && item.iperf >= 0)
  )

  const maxValue = Math.max(
    1,
    ...points.flatMap(p => [p.mini, p.iperf].filter(v => v !== null && Number.isFinite(v)))
  )
  const axisMax = Math.ceil(maxValue / 10) * 10 || 10
  const x = index => left + (points.length <= 1 ? plotWidth / 2 : index * plotWidth / (points.length - 1))
  const y = value => top + plotHeight - (value / axisMax) * plotHeight

  const makePath = key => {
    let path = ''
    let drawing = false
    points.forEach((point, index) => {
      const value = point[key]
      if (value === null || !Number.isFinite(value) || value < 0) {
        drawing = false
        return
      }
      path += `${drawing ? ' L' : ' M'} ${x(index)} ${y(value)}`
      drawing = true
    })
    return path
  }

  return (
    <article className="throughput-chart-card">
      <h3>{title}</h3>
      <p className="throughput-chart-subtitle">
        Historical throughput ? Mbps ? {points.length} completed sessions with data
      </p>

      {points.length === 0 ? (
        <p>No completed-session measurements are available yet.</p>
      ) : (
        <>
          <div style={{ width: '100%', overflowX: 'auto' }}>
            <svg
              viewBox={`0 0 ${width} ${height}`}
              role="img"
              aria-label={`${title}: historical Mini-Ookla and iperf3 throughput`}
              style={{ width: '100%', minWidth: points.length > 12 ? '650px' : '0', display: 'block' }}
            >
              {[0, 1, 2, 3, 4].map(i => {
                const value = axisMax * i / 4
                const yy = y(value)
                return (
                  <g key={i}>
                    <line x1={left} y1={yy} x2={width - right} y2={yy}
                      stroke="currentColor" strokeOpacity="0.15" />
                    <text x={left - 9} y={yy + 4} textAnchor="end"
                      fill="currentColor" fontSize="10">{value.toFixed(0)}</text>
                  </g>
                )
              })}

              {points.map((point, index) => (
                <g key={point.session_id || index}>
                  <text
                    x={x(index)}
                    y={height - 23}
                    textAnchor="end"
                    transform={`rotate(-35 ${x(index)} ${height - 23})`}
                    fill="currentColor"
                    fontSize="9"
                  >
                    {index + 1}
                  </text>
                  <title>{`Session ${index + 1}: ${point.session_id || ''}`}</title>
                </g>
              ))}

              <path d={makePath('mini')} fill="none" stroke="#19d3c5"
                strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
              <path d={makePath('iperf')} fill="none" stroke="#7c9cff"
                strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />

              {points.map((point, index) => (
                <g key={`dots-${point.session_id || index}`}>
                  {point.mini !== null && Number.isFinite(point.mini) && point.mini >= 0 && (
                    <circle cx={x(index)} cy={y(point.mini)} r="3.5" fill="#19d3c5">
                      <title>{`Session ${index + 1} ? Mini-Ookla: ${point.mini.toFixed(2)} Mbps`}</title>
                    </circle>
                  )}
                  {point.iperf !== null && Number.isFinite(point.iperf) && point.iperf >= 0 && (
                    <circle cx={x(index)} cy={y(point.iperf)} r="3.5" fill="#7c9cff">
                      <title>{`Session ${index + 1} ? iperf3: ${point.iperf.toFixed(2)} Mbps`}</title>
                    </circle>
                  )}
                </g>
              ))}
              <text x={left + plotWidth / 2} y={height - 2}
                textAnchor="middle" fill="currentColor" fontSize="10">Completed session order (oldest ? newest)</text>
            </svg>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '22px', fontSize: '12px', marginTop: '8px' }}>
            <span><span style={{ color: '#19d3c5' }}>?</span> Mini-Ookla</span>
            <span><span style={{ color: '#7c9cff' }}>?</span> iperf3</span>
          </div>
        </>
      )}
    </article>
  )
}


function LineChart({ history = [] }) {
  const records = [...history]
    .filter(record => record && record.id != null)
    .sort((a, b) => Number(a.id) - Number(b.id))

  const width = 700
  const height = 220
  const left = 48
  const right = 16
  const top = 16
  const bottom = 12
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom

  const toNumber = value => {
    if (value === null || value === undefined || value === '') {
      return null
    }

    const number = Number(value)
    return Number.isFinite(number) && number >= 0 ? number : null
  }

  const download = records.map(r => toNumber(r.download_mbps))
  const upload = records.map(r => toNumber(r.upload_mbps))
  const values = [...download, ...upload].filter(v => v !== null)

  if (records.length === 0 || values.length === 0) {
    return <p>No valid measurement history available yet.</p>
  }

  const maxValue = Math.max(...values)
  const axisMax = Math.max(10, Math.ceil(maxValue / 10) * 10)
  const ticks = Array.from(
    { length: 5 },
    (_, i) => axisMax * (1 - i / 4)
  )

  const xAt = index =>
    left + (
      records.length > 1
        ? index / (records.length - 1) * plotWidth
        : plotWidth / 2
    )

  const yAt = value =>
    top + plotHeight * (1 - value / axisMax)

  const makeSegments = series => {
    const segments = []
    let current = []

    series.forEach((value, index) => {
      if (value === null) {
        if (current.length) segments.push(current)
        current = []
      } else {
        current.push(`${xAt(index)},${yAt(value)}`)
      }
    })

    if (current.length) segments.push(current)
    return segments
  }

  return (
    <svg
      className="line-chart"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`Download and upload throughput history, zero to ${axisMax} Mbps`}
    >
      {ticks.map(value => {
        const y = yAt(value)

        return (
          <g key={value}>
            <line
              x1={left}
              y1={y}
              x2={width - right}
              y2={y}
              className="chart-grid"
            />
            <text
              x={left - 10}
              y={y + 4}
              textAnchor="end"
              className="chart-axis-label"
            >
              {value.toFixed(0)}
            </text>
          </g>
        )
      })}

      {makeSegments(download).map((segment, index) => (
        <polyline
          key={`download-${index}`}
          points={segment.join(' ')}
          className="chart-line download"
        />
      ))}

      {makeSegments(upload).map((segment, index) => (
        <polyline
          key={`upload-${index}`}
          points={segment.join(' ')}
          className="chart-line upload"
        />
      ))}

      {download.map((value, index) =>
        value === null ? null : (
          <circle
            key={`download-point-${records[index].id}`}
            cx={xAt(index)}
            cy={yAt(value)}
            r="2.5"
            className="chart-point download-point"
          />
        )
      )}

      {upload.map((value, index) =>
        value === null ? null : (
          <circle
            key={`upload-point-${records[index].id}`}
            cx={xAt(index)}
            cy={yAt(value)}
            r="2.5"
            className="chart-point upload-point"
          />
        )
      )}
    </svg>
  )
}



function ComparisonPage({ history = [] }) {
  const usingSampleData = history.length === 0;
const sourceResults = usingSampleData ? sampleResults : history;

const results = [...sourceResults]
  .filter((r) => r && r.id != null)
  .sort((a, b) => Number(a.id) - Number(b.id));

const sampleCount = results.length;

  const number = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  };

  const format = (value) => {
    const n = number(value);
    return n === null ? '—' : n.toFixed(2);
  };

  const jitterOf = (r) => number(r.jitter_ms ?? r.jitter);
  const lossOf = (r) => number(r.packet_loss_percent ?? r.packet_loss);
  const serverName = (id) => ({
    server_01: 'Server A',
    server_02: 'Server B',
    server_03: 'Server C',
  }[id] || id || 'Unknown');

  const chartWidth = 460;
  const chartHeight = 190;
  const left = 38;
  const right = 12;
  const top = 15;
  const bottom = 30;
  const plotWidth = chartWidth - left - right;
  const plotHeight = chartHeight - top - bottom;

  const chartFrame = (maxValue, label) => (
    <>
      {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
        const y = top + plotHeight * fraction;
        return (
          <g key={fraction}>
            <line
              x1={left}
              y1={y}
              x2={chartWidth - right}
              y2={y}
              className="graph-grid"
            />
            <text
              x={left - 7}
              y={y + 3}
              textAnchor="end"
              className="graph-axis-label"
            >
              {(maxValue * (1 - fraction)).toFixed(0)}
            </text>
          </g>
        );
      })}
      <text
        x={10}
        y={top + plotHeight / 2}
        textAnchor="middle"
        className="graph-axis-title"
        transform={`rotate(-90 10 ${top + plotHeight / 2})`}
      >
        {label}
      </text>
    </>
  );

  const validThroughput = results.filter(
    (r) => number(r.download_mbps) !== null &&
           number(r.upload_mbps) !== null
  );

  const throughputMax = Math.max(
    1,
    ...results.flatMap((r) => [
      number(r.download_mbps) ?? 0,
      number(r.upload_mbps) ?? 0,
    ])
  );

  const latencyRecords = results.filter(
    (r) => number(r.latency_ms) !== null
  );

  const latencyMax = Math.max(
    1,
    ...latencyRecords.map((r) => number(r.latency_ms) ?? 0)
  );

  const qualityRecords = results.filter(
    (r) => jitterOf(r) !== null || lossOf(r) !== null
  );

const serverIds = ['server_01', 'server_02', 'server_03'];

const latestQualityRecords = serverIds
  .map((id) =>
    results
      .filter((r) => r.server_id === id)
      .reduce(
        (latest, current) =>
          !latest || Number(current.id) > Number(latest.id)
            ? current
            : latest,
        null
      )
  )
  .filter(Boolean);



const serverRecords = serverIds.map((id) => {
  const records = results.filter((r) => r.server_id === id);

  const latest = records.reduce(
    (best, current) =>
      !best || Number(current.id) > Number(best.id)
        ? current
        : best,
    null
  );

  const downloadValues = records
    .map((r) => number(r.download_mbps))
    .filter((value) => value !== null);

  const uploadValues = records
    .map((r) => number(r.upload_mbps))
    .filter((value) => value !== null);

  const averageDownload = downloadValues.length
    ? downloadValues.reduce((sum, value) => sum + value, 0)
        / downloadValues.length
    : null;

  const averageUpload = uploadValues.length
    ? uploadValues.reduce((sum, value) => sum + value, 0)
        / uploadValues.length
    : null;

  return {
    id,
    latest,
    count: records.length,
    averageDownload,
    averageUpload,
  };
});


  const performanceMax = Math.max(
    1,
    ...serverRecords.flatMap(({ latest }) => [
      number(latest?.download_mbps) ?? 0,
      number(latest?.upload_mbps) ?? 0,
    ])
  );

  const stabilityRecords = results.filter(
    (r) => number(r.download_mbps) !== null
  );

  const stabilityMax = Math.max(
    1,
    ...stabilityRecords.map((r) => number(r.download_mbps) ?? 0)
  );
// ADD THE NEW CODE HERE
const stabilityValues = stabilityRecords
  .map((r) => number(r.download_mbps))
  .filter((value) => value !== null);

const stabilityAverage = stabilityValues.length
  ? stabilityValues.reduce((sum, value) => sum + value, 0)
      / stabilityValues.length
  : null;

const stabilityStdDev = stabilityValues.length
  ? Math.sqrt(
      stabilityValues.reduce(
        (sum, value) => sum + (value - stabilityAverage) ** 2,
        0
      ) / stabilityValues.length
    )
  : null;

// EXISTING CODE CONTINUES BELOW
  const linePoints = (records, getter, max) =>
    records
      .filter((r) => getter(r) !== null)
      .map((r) => {
        const index = validThroughput.findIndex((item) => item.id === r.id);
        const x = left + (
          validThroughput.length > 1
            ? index / (validThroughput.length - 1) * plotWidth
            : plotWidth / 2
        );
        const y = top + plotHeight * (1 - getter(r) / max);
        return `${x},${y}`;
      })
      .join(' ');

  if (results.length === 0) {
    return (
      <div className="comparison-page">
        <div className="panel comparison-card">
          <h2>No measurements available yet</h2>
          <p>Stored backend measurements will appear here when available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="comparison-page">
      <div className="comparison-notice">
      {usingSampleData
        ? 'Illustrative sample data — these values are not real measurements.'
        : "Showing saved backend measurements. Results from different servers may not belong to the same test session."}
      </div>

      <section className="comparison-grid">
        <article className="panel comparison-card">
          <h2>1. Throughput Over Time</h2>
          <p>Download and upload speed · Mbps</p>

          {validThroughput.length === 0 ? (
            <p>No valid throughput measurements are available.</p>
          ) : (
            <>
              <div className="graph-scroll">
                <svg
                  className="comparison-graph"
                  viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                  role="img"
                  aria-label="Download and upload throughput over recorded tests"
                >
                  {chartFrame(throughputMax, 'Mbps')}
                  <polyline
                    points={linePoints(validThroughput, r => number(r.download_mbps), throughputMax)}
                    className="graph-line graph-download"
                  />
                  <polyline
                    points={linePoints(validThroughput, r => number(r.upload_mbps), throughputMax)}
                    className="graph-line graph-upload"
                  />
                  {validThroughput.map((r, i) => {
                    const x = left + (
                      validThroughput.length > 1
                        ? i / (validThroughput.length - 1) * plotWidth
                        : plotWidth / 2
                    );
                    return (
                      <g key={r.id}>
                        <circle
                          cx={x}
                          cy={top + plotHeight * (1 - r.download_mbps / throughputMax)}
                          r="3"
                          className="graph-point-download"
                        />
                        <circle
                          cx={x}
                          cy={top + plotHeight * (1 - r.upload_mbps / throughputMax)}
                          r="3"
                          className="graph-point-upload"
                        />
                        <text
                          x={x}
                          y={chartHeight - 8}
                          textAnchor="middle"
                          className="graph-axis-label"
                        >
                          {r.id}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
              <div className="comparison-legend">
                <span className="legend-download">↓ Download</span>
                <span className="legend-upload">↑ Upload</span>
              </div>
            </>
          )}
        </article>

        <article className="panel comparison-card">
          <h2>2. Network Quality</h2>
          <p>Latency and jitter · ms; packet loss · %</p>

          <div className="quality-list">
            {latestQualityRecords.map((r) => (
              <div className="quality-row" key={r.id}>
                <div className="quality-row-heading">
                  <strong>{serverName(r.server_id)}</strong>
                  <span>Test {r.id}</span>
                </div>
                <div className="quality-metrics">
                  <span>Latency <b>{format(r.latency_ms)} ms</b></span>
                  <span>Jitter <b>{format(jitterOf(r))} ms</b></span>
                  <span>Loss <b>{format(lossOf(r))}%</b></span>
                </div>
                {number(r.latency_ms) !== null && (
                  <div className="quality-track" aria-label="Latency relative to the largest recorded latency">
                    <div
                      className="quality-fill"
                      style={{ width: `${Math.min(100, number(r.latency_ms) / latencyMax * 100)}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="comparison-legend">
            <span className="legend-latency">~ Latency scale</span>
            <span>Jitter and loss shown numerically</span>
          </div>
        </article>

        <article className="panel comparison-card">
          <h2>3. Server Performance</h2>
          <p>Average throughput and latest result per server · Mbps</p>

          <div className="server-chart">
            {serverRecords.map(({ id, latest, count, averageDownload, averageUpload }) => (
              <div className="server-chart-row" key={id}>
                <div className="server-chart-label">
                  <strong>{serverName(id)}</strong>
                  <small>{count} recorded {count === 1 ? 'test' : 'tests'}</small>
                </div>
                <div className="server-bars">
                  <div className="server-bar-line">
                    <span className="server-bar-caption">↓</span>
                    <div className="server-bar-track">
                      <div
                        className="server-bar graph-download"
                        style={{
                          width: `${(averageDownload ?? 0) / performanceMax * 100}%`,
                        }}
                      />
                    </div>
                    <b>{format(averageDownload)}</b>
                  </div>
                  <div className="server-bar-line">
                    <span className="server-bar-caption">↑</span>
                    <div className="server-bar-track">
                      <div
                        className="server-bar graph-upload"
                        style={{
                          width: `${(averageUpload ?? 0) / performanceMax * 100}%`,
                        }}
                      />
                    </div>
                    <b>{format(averageUpload)}</b>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="comparison-legend">
            <span className="legend-download">↓ Download</span>
            <span className="legend-upload">↑ Upload</span>
          </div>
        </article>

        <article className="panel comparison-card">
          <h2>4. Stability & Distribution</h2>
          <p>Recorded download speeds · Mbps</p>

          {stabilityRecords.length < 2 ? (
            <div className="graph-empty">
              At least two recorded download measurements are needed to show
              variation. Current sample count: {stabilityRecords.length}.
            </div>
          ) : (
            <>
              <div className="graph-scroll">
                <svg
                  className="comparison-graph"
                  viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                  role="img"
                  aria-label="Download speed distribution across recorded tests"
                >
                  {chartFrame(stabilityMax, 'Mbps')}
                  {stabilityRecords.map((r, i) => {
                    const x = left + (
                      stabilityRecords.length > 1
                        ? i / (stabilityRecords.length - 1) * plotWidth
                        : plotWidth / 2
                    );
                    const y = top + plotHeight * (
                      1 - (number(r.download_mbps) ?? 0) / stabilityMax
                    );
                    return (
                      <g key={r.id}>
                        <line
                          x1={x}
                          y1={y}
                          x2={x}
                          y2={top + plotHeight}
                          className="distribution-stem"
                        />
                        <circle cx={x} cy={y} r="4" className="graph-point-download" />
                        <text
                          x={x}
                          y={chartHeight - 8}
                          textAnchor="middle"
                          className="graph-axis-label"
                        >
                          {r.id}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
              <div className="stability-summary">
                <div>
                  <span>Lowest</span>
                  <strong>{format(Math.min(...stabilityRecords.map(r => number(r.download_mbps))))} Mbps</strong>
                </div>
                <div>
                  <span>Highest</span>
                  <strong>{format(Math.max(...stabilityRecords.map(r => number(r.download_mbps))))} Mbps</strong>
                </div>
                <div>
                  <span>Range</span>
                  <strong>{format(
                    Math.max(...stabilityRecords.map(r => number(r.download_mbps))) -
                    Math.min(...stabilityRecords.map(r => number(r.download_mbps)))
                  )} Mbps</strong>

                </div>
                                <div>
                  <span>Average</span>
                  <strong>{format(stabilityAverage)} Mbps</strong>
                </div>
                <div>
                  <span>Std. deviation</span>
                  <strong>{format(stabilityStdDev)} Mbps</strong>
                </div>
              </div>
              <p className="graph-footnote">
                This shows the spread of recorded values, not a statistical
                guarantee of future network stability.
              </p>
            </>
          )}
        </article>
      </section>
      <ValidationAverageCharts />
    </div>
  );
}


function ValidationAverageCharts() {
  const [averages, setAverages] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function loadAverages() {
      setLoading(true);
      setError('');

      try {
        const response = await fetch('/api/validation/sessions');
        if (!response.ok) {
          throw new Error(`Session API returned HTTP ${response.status}`);
        }

        const payload = await response.json();
        const sessions = Array.isArray(payload)
          ? payload
          : payload.sessions;

        if (!Array.isArray(sessions)) {
          throw new Error('Unexpected validation session response');
        }

        const completed = sessions.filter(session =>
          session.status === 'completed' &&
          session.mini_ookla_status === 'completed' &&
          session.iperf3_status === 'completed' &&
          session.session_id
        );

        const details = await Promise.all(
          completed.map(async session => {
            try {
              const result = await fetch(
                `/api/validation/sessions/${encodeURIComponent(session.session_id)}`
              );

              if (!result.ok) return null;

              const detail = await result.json();
              const miniResults = detail.mini_ookla_results;
              const iperfResults = detail.iperf3_results;

              if (
                !Array.isArray(miniResults) || !miniResults.length ||
                !Array.isArray(iperfResults) || !iperfResults.length
              ) {
                return null;
              }

              // Use the newest result from each tool in this session.
              const newest = rows => [...rows].sort((a, b) => {
                const timeA = Date.parse(a.timestamp || '') || 0;
                const timeB = Date.parse(b.timestamp || '') || 0;
                return timeB - timeA || Number(b.id || 0) - Number(a.id || 0);
              })[0];

              return {
                mini: newest(miniResults),
                iperf: newest(iperfResults),
              };
            } catch {
              return null;
            }
          })
        );

        const paired = details.filter(Boolean);

        const average = values => {
          const valid = values
            .map(Number)
            .filter(value => Number.isFinite(value));

          return valid.length
            ? valid.reduce((sum, value) => sum + value, 0) / valid.length
            : null;
        };

        const next = {
          count: paired.length,
          miniDownload: average(paired.map(item => item.mini.download_mbps)),
          iperfDownload: average(paired.map(item => item.iperf.download_mbps)),
          miniUpload: average(paired.map(item => item.mini.upload_mbps)),
          iperfUpload: average(paired.map(item => item.iperf.upload_mbps)),
        };

        if (!cancelled) setAverages(next);
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Could not load validation averages');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadAverages();
    return () => {
      cancelled = true;
    };
  }, []);

  const formatMbps = value =>
    value === null || !Number.isFinite(value) ? '—' : value.toFixed(2);

  const Comparison = ({ title, mini, iperf, arrow }) => {
    const max = Math.max(1, mini ?? 0, iperf ?? 0);

    return (
      <article className="panel comparison-card">
        <h3>{arrow} {title}</h3>
        <p>Average throughput · Mbps</p>

        {[['Mini-Ookla', mini, 'graph-download'],
          ['iperf3', iperf, 'graph-upload']].map(([name, value, color]) => (
          <div className="server-chart-row" key={name}>
            <div className="server-chart-label">
              <strong>{name}</strong>
            </div>
            <div className="server-bars">
              <div className="validation-bar-line">
                <div className="server-bar-track">
                  <div
                    className={`server-bar ${color}`}
                    style={{
                      width: `${Math.max(0, value ?? 0) / max * 100}%`,
                    }}
                  />
                </div>
                <b>{formatMbps(value)}</b>
              </div>
            </div>
          </div>
        ))}
      </article>
    );
  };

  return (
    <section className="panel comparison-card validation-averages">
      <h2>5. Validation Session Averages</h2>
      <p>
        Mini-Ookla versus iperf3 · completed sessions with both saved results
      </p>

      {loading ? (
        <p>Loading validation averages…</p>
      ) : error ? (
        <p role="alert">{error}</p>
      ) : !averages || averages.count === 0 ? (
        <p>No completed paired validation measurements are available.</p>
      ) : (
        <>
          <p>Based on {averages.count} paired completed sessions.</p>
          <div className="throughput-charts-grid">
            <Comparison
              title="Download"
              arrow="↓"
              mini={averages.miniDownload}
              iperf={averages.iperfDownload}
            />
            <Comparison
              title="Upload"
              arrow="↑"
              mini={averages.miniUpload}
              iperf={averages.iperfUpload}
            />
          </div>
          <div className="comparison-legend">
            <span className="legend-download">Mini-Ookla</span>
            <span className="legend-upload">iperf3</span>
          </div>
          <p className="graph-footnote">
            These are overall validation averages, not per-server iperf3
            averages. The saved iperf3 records do not currently identify
            individual servers.
          </p>
        </>
      )}
    </section>
  );
}



function Iperf3Page({ history = [], loading, error }) {
  const records = [...history].sort(
    (a, b) => Number(a.id) - Number(b.id)
  )

  const validNumber = value => {
    if (value === null || value === undefined || value === '') {
      return null
    }

    const number = Number(value)
    return Number.isFinite(number) ? number : null
  }




  const format = value => {
    const number = validNumber(value)
    return number === null ? '—' : number.toFixed(2)
  }

  const validRecords = records.filter(
    record =>
      validNumber(record.download_mbps) !== null &&
      validNumber(record.upload_mbps) !== null
  )

  const maxSpeed = Math.max(
    1,
    ...validRecords.flatMap(record => [
      validNumber(record.download_mbps),
      validNumber(record.upload_mbps),
    ])
  )

  const chartWidth = 600
  const chartHeight = 220
  const left = 45
  const right = 15
  const top = 15
  const bottom = 35
  const plotWidth = chartWidth - left - right
  const plotHeight = chartHeight - top - bottom

  const point = (record, index, field) => {
    const x = left + (
      validRecords.length > 1
        ? index / (validRecords.length - 1) * plotWidth
        : plotWidth / 2
    )

    const y = top + plotHeight * (
      1 - validNumber(record[field]) / maxSpeed
    )

    return `${x},${y}`
  }

  const diagnostic = record => {
    const details = [
      record.test_id,
      record.raw_output,
      record.metrics?.test_type,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()

    return details.includes('diagnostic') ||
      details.includes('manual api') ||
      details.includes('backend integration verification')
  }

  const linePoints = field =>
    validRecords
      .map((record, index) => point(record, index, field))
      .join(' ')

  return (
    <div className="iperf3-page">
      <div className="comparison-notice">
        iperf3 TCP measurements · Separate from Mini-Ookla results
      </div>

      {error && (
        <div className="graph-empty">
          Unable to load iperf3 measurements: {error}
        </div>
      )}

      <section className="metrics-grid">
        <MetricCard
          icon="↓"
          label="Latest download"
          value={validRecords.length
            ? format(validRecords[validRecords.length - 1].download_mbps)
            : '—'}
          unit=" Mbps"
          tone="blue"
          foot="Latest saved iperf3 result"
        />

        <MetricCard
          icon="↑"
          label="Latest upload"
          value={validRecords.length
            ? format(validRecords[validRecords.length - 1].upload_mbps)
            : '—'}
          unit=" Mbps"
          tone="purple"
          foot="Latest saved iperf3 result"
        />

        <MetricCard
          icon="#"
          label="Saved measurements"
          value={String(records.length)}
          unit=""
          tone="cyan"
          foot="Records returned by backend"
        />

        <MetricCard
          icon="OK"
          label="Valid throughput"
          value={String(validRecords.length)}
          unit=""
          tone="amber"
          foot="Records with both speeds"
        />
      </section>

      <article className="panel comparison-card">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">IPERF3 TELEMETRY</span>
            <h2>TCP Throughput Over Time</h2>
            <p>Download and upload · Mbps</p>
          </div>
          <span className="count-tag">
            {validRecords.length} measurements
          </span>
        </div>

        {loading ? (
          <p>Loading iperf3 history...</p>
        ) : validRecords.length === 0 ? (
          <p>No valid throughput measurements available.</p>
        ) : (
          <>
            <div className="graph-scroll">
              <svg
                className="comparison-graph"
                viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                role="img"
                aria-label="iperf3 download and upload throughput history"
              >
                {[0, 0.25, 0.5, 0.75, 1].map(fraction => {
                  const y = top + plotHeight * fraction
                  return (
                    <g key={fraction}>
                      <line
                        x1={left}
                        y1={y}
                        x2={chartWidth - right}
                        y2={y}
                        className="graph-grid"
                      />
                      <text
                        x={left - 8}
                        y={y + 3}
                        textAnchor="end"
                        className="graph-axis-label"
                      >
                        {(maxSpeed * (1 - fraction)).toFixed(0)}
                      </text>
                    </g>
                  )
                })}

                <polyline
                  points={linePoints('download_mbps')}
                  className="graph-line graph-download"
                />

                <polyline
                  points={linePoints('upload_mbps')}
                  className="graph-line graph-upload"
                />

                {validRecords.map((record, index) => {
                  const x = left + (
                    validRecords.length > 1
                      ? index / (validRecords.length - 1) * plotWidth
                      : plotWidth / 2
                  )

                  return (
                    <text
                      key={record.id}
                      x={x}
                      y={chartHeight - 10}
                      textAnchor="middle"
                      className="graph-axis-label"
                    >
                      {record.id}
                    </text>
                  )
                })}
              </svg>
            </div>

            <div className="comparison-legend">
              <span className="legend-download">↓ Download</span>
              <span className="legend-upload">↑ Upload</span>
            </div>
            <p className="graph-footnote">
              The vertical scale adjusts to the largest displayed speed.
              Records are ordered by ID; gaps in timestamps are not
              represented as proportional time intervals.
            </p>
          </>
        )}
      </article>

      <article className="panel history-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">MEASUREMENT LOG</span>
            <h2>iperf3 Measurement History</h2>
            <p>Saved results from the iperf3 backend endpoint</p>
          </div>
          <span className="count-tag">{records.length} records</span>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Test</th>
                <th>Server</th>
                <th>Download</th>
                <th>Upload</th>
                <th>Duration</th>
                <th>Streams</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {records.map(record => (
                <tr key={record.id}>
                  <td>#{record.id}</td>
                  <td>
                    {diagnostic(record)
                      ? 'Diagnostic'
                      : record.test_id || 'Unlabelled'}
                  </td>
                  <td>
                    {record.server_id || record.host || 'Unknown'}
                  </td>
                  <td className="cyan-cell">
                    {format(record.download_mbps)} Mbps
                  </td>
                  <td className="purple-cell">
                    {format(record.upload_mbps)} Mbps
                  </td>
                  <td>{format(record.duration_sec)} s</td>
                  <td>{record.streams ?? '—'}</td>
                  <td>{record.timestamp || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="table-foot">
          Missing metadata is shown as unavailable. Diagnostic records are
          identified separately; the table does not assume every record
          represents an ordinary speed test.
        </div>
      </article>
    </div>
  )
}



function MeasurementHistoryPage({ history = [], query = '' }) {
  const format = (value, decimals = 2) => {
    if (value === null || value === undefined || value === '') {
      return '—'
    }

    const number = Number(value)
    return Number.isFinite(number) ? number.toFixed(decimals) : '—'
  }

  const records = [...history]
    .filter(record => record && record.id != null)
    .filter(record =>
      `${record.id} ${record.server_id ?? ''} ${record.timestamp ?? ''}`
        .toLowerCase()
        .includes(query.toLowerCase())
    )
    .sort((a, b) => Number(b.id) - Number(a.id))

  // Group records by server
  const serverGroups = records.reduce((groups, record) => {
    const server = record.server_id || 'Unknown'
    if (!groups[server]) {
      groups[server] = []
    }
    groups[server].push(record)
    return groups
  }, {})

  // Sort server names naturally: server_01, server_02, server_03
  const sortedServers = Object.keys(serverGroups).sort((a, b) =>
    a.localeCompare(b, undefined, {
      numeric: true,
      sensitivity: 'base',
    })
  )

  const latestRecord = [...history]
    .filter(record => record && record.id != null)
    .sort((a, b) => Number(b.id) - Number(a.id))[0]

  return (
    <div className="history-page">
      <div className="comparison-notice">
        Mini-Ookla measurements · Separate from iperf3 results
      </div>

      <section className="metrics-grid">
        <MetricCard
          icon="#"
          label="Total measurements"
          value={String(history.length)}
          unit=""
          tone="cyan"
          foot="Records returned by backend"
        />

        <MetricCard
          icon="↓"
          label="Latest download"
          value={format(latestRecord?.download_mbps)}
          unit=" Mbps"
          tone="blue"
          foot="Latest saved record"
        />

        <MetricCard
          icon="↑"
          label="Latest upload"
          value={format(latestRecord?.upload_mbps)}
          unit=" Mbps"
          tone="purple"
          foot="Latest saved record"
        />

        <MetricCard
          icon="=="
          label="Matching records"
          value={String(records.length)}
          unit=""
          tone="amber"
          foot="Based on search filter"
        />
      </section>

      {sortedServers.map(server => (
        <article className="panel history-panel" key={server}>
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">MEASUREMENT ARCHIVE</span>
              <h2>
                {server === 'Unknown' ? 'Unknown Server' : server}
              </h2>
              <p>Saved Mini-Ookla records, newest first</p>
            </div>
            <span className="count-tag">
              {serverGroups[server].length} records
            </span>
          </div>

          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Server</th>
                  <th>Download</th>
                  <th>Upload</th>
                  <th>Latency</th>
                  <th>Jitter</th>
                  <th>Packet loss</th>
                  <th>Timestamp</th>
                </tr>
              </thead>

              <tbody>
                {serverGroups[server].map(record => (
                  <tr key={record.id}>
                    <td className="muted-cell">#{record.id}</td>
                    <td>{record.server_id || 'Unknown'}</td>
                    <td className="cyan-cell">
                      {format(record.download_mbps)} Mbps
                    </td>
                    <td className="purple-cell">
                      {format(record.upload_mbps)} Mbps
                    </td>
                    <td>{format(record.latency_ms)} ms</td>
                    <td>
                      {format(record.jitter_ms ?? record.jitter)} ms
                    </td>
                    <td>
                      {format(
                        record.packet_loss_percent ?? record.packet_loss
                      )}%
                    </td>
                    <td>{record.timestamp || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="table-foot">
            Showing saved backend measurements. Missing values are
            displayed as unavailable rather than treated as zero.
          </div>
        </article>
      ))}

      {records.length === 0 && (
        <div className="panel graph-empty">
          No matching measurements found.
        </div>
      )}
    </div>
  )
}



function ValidationSessionsPage() {
  const [sessions, setSessions] = useState([])
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [selectedSession, setSelectedSession] = useState(null)
  const [historicalSessions, setHistoricalSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [detailError, setDetailError] = useState('')

  useEffect(() => {
    let cancelled = false
    let fetching = false

    async function loadSessions() {
      if (fetching) return
      fetching = true

      try {
        const response = await fetch('/api/validation/sessions')
        if (!response.ok) {
          throw new Error(`Session API returned HTTP ${response.status}`)
        }

        const data = await response.json()
        const items = Array.isArray(data) ? data : data.sessions

        if (!Array.isArray(items)) {
          throw new Error('Unexpected validation session response format')
        }

        if (!cancelled) {
          setSessions(items)
          setError('')
          setSelectedSessionId(current =>
            current && items.some(item => item.session_id === current)
              ? current
              : items[0]?.session_id || ''
          )
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Unable to load validation sessions')
        }
      } finally {
        fetching = false
        if (!cancelled) setLoading(false)
      }
    }

    loadSessions()
    const timer = setInterval(loadSessions, 5000)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  // Load paired measurements for every fully completed validation session.
  // This effect belongs here (not in Iperf3Page), because it uses the
  // validation session list and populates the historical comparison graphs.
  useEffect(() => {
    let cancelled = false

    const latest = records => {
      if (!Array.isArray(records) || records.length === 0) return null

      return [...records].sort((a, b) => {
        const timeA = Date.parse(a.timestamp || '') || 0
        const timeB = Date.parse(b.timestamp || '') || 0
        return timeB - timeA || Number(b.id || 0) - Number(a.id || 0)
      })[0]
    }

    async function loadHistoricalSessions() {
      const completed = sessions.filter(item =>
        String(item.status || '').toLowerCase() === 'completed' &&
        String(item.mini_ookla_status || '').toLowerCase() === 'completed' &&
        String(item.iperf3_status || '').toLowerCase() === 'completed' &&
        Boolean(item.session_id)
      )

      try {
        const details = await Promise.all(
          completed.map(async item => {
            try {
              const response = await fetch(
                `/api/validation/sessions/${encodeURIComponent(item.session_id)}`
              )
              if (!response.ok) {
                console.warn(
                  'Could not load historical session:',
                  item.session_id,
                  response.status
                )
                return null
              }

              const detail = await response.json()
              const mini = latest(detail.mini_ookla_results)
              const iperf = latest(detail.iperf3_results)

              // Keep only paired sessions that have both saved result records.
              if (!mini || !iperf) return null

              return {
                session_id: detail.session_id || item.session_id,
                created_at: detail.created_at || item.created_at || '',
                mini,
                iperf,
              }
            } catch (err) {
              console.warn(
                'Could not read historical session:',
                item.session_id,
                err
              )
              return null
            }
          })
        )

        if (!cancelled) {
          const usable = details
            .filter(Boolean)
            .sort((a, b) =>
              (Date.parse(a.created_at || '') || 0) -
              (Date.parse(b.created_at || '') || 0)
            )

          console.log('Historical graph sessions loaded:', usable.length)
          setHistoricalSessions(usable)
        }
      } catch (err) {
        console.error('Historical validation graph loading failed:', err)
        if (!cancelled) setHistoricalSessions([])
      }
    }

    if (sessions.length > 0) {
      loadHistoricalSessions()
    } else {
      setHistoricalSessions([])
    }

    return () => {
      cancelled = true
    }
  }, [sessions])

  useEffect(() => {
    if (!selectedSessionId) {
      setSelectedSession(null)
      return undefined
    }

    let cancelled = false
    let fetching = false

    async function loadSessionDetails() {
      if (fetching) return
      fetching = true
      setDetailLoading(true)

      try {
        const response = await fetch(
          `/api/validation/sessions/${encodeURIComponent(selectedSessionId)}`
        )
        if (!response.ok) {
          throw new Error(`Session details returned HTTP ${response.status}`)
        }

        const data = await response.json()
        if (!cancelled) {
          setSelectedSession(data)
          setDetailError('')
        }
      } catch (err) {
        if (!cancelled) {
          setDetailError(err.message || 'Unable to load session details')
        }
      } finally {
        fetching = false
        if (!cancelled) setDetailLoading(false)
      }
    }

    loadSessionDetails()
    const timer = setInterval(loadSessionDetails, 5000)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [selectedSessionId])

  const format = value => {
    if (value === null || value === undefined || value === '') return '—'
    const number = Number(value)
    return Number.isFinite(number) ? number.toFixed(2) : String(value)
  }

  const latest = records => {
    if (!Array.isArray(records) || records.length === 0) return null
    return [...records].sort((a, b) => {
      const timeA = Date.parse(a.timestamp || '') || 0
      const timeB = Date.parse(b.timestamp || '') || 0
      return timeB - timeA || Number(b.id || 0) - Number(a.id || 0)
    })[0]
  }

  const mini = latest(selectedSession?.mini_ookla_results)
  const iperf = latest(selectedSession?.iperf3_results)
  const session = selectedSession
  const status = String(session?.status || 'unknown').toLowerCase()

  const statusClass = value =>
    `validation-status status-${String(value || 'unknown').toLowerCase()}`

  const comparisonRows = [
    { label: 'Download', key: 'download_mbps', unit: 'Mbps' },
    { label: 'Upload', key: 'upload_mbps', unit: 'Mbps' },
  ]

  return (
    <div className="validation-page">
      <div className="comparison-notice">
        Measurements are compared only when they belong to the selected validation session.
      </div>

      <section className="metrics-grid">
        <MetricCard
          icon="#"
          label="Validation sessions"
          value={String(sessions.length)}
          unit=""
          tone="cyan"
          foot="Sessions returned by backend"
        />
        <MetricCard
          icon="OK"
          label="Completed"
          value={String(sessions.filter(s => s.status === 'completed').length)}
          unit=""
          tone="blue"
          foot="Both tests completed"
        />
        <MetricCard
          icon=">>"
          label="Running"
          value={String(sessions.filter(s => s.status === 'running').length)}
          unit=""
          tone="amber"
          foot="In progress or pending"
        />
        <MetricCard
          icon="!"
          label="Partial / failed"
          value={String(sessions.filter(s =>
            ['partial', 'failed'].includes(String(s.status).toLowerCase())
          ).length)}
          unit=""
          tone="purple"
          foot="At least one test did not complete"
        />
      </section>

      <article className="panel history-panel validation-sessions-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">VALIDATION ARCHIVE</span>
            <h2>Validation Sessions</h2>
            <p>Select a session to inspect the measurements linked to it.</p>
          </div>
          <span className="count-tag">{sessions.length} sessions</span>
        </div>

        {error && <div className="graph-empty">{error}</div>}
        {loading && <div className="graph-empty">Loading validation sessions...</div>}

        {!loading && !error && sessions.length === 0 && (
          <div className="graph-empty">
            No validation sessions have been recorded yet. A session will appear
            here after the combined workflow creates one.
          </div>
        )}

        {sessions.length > 0 && (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Session ID</th>
                  <th>Mini-Ookla</th>
                  <th>iperf3</th>
                  <th>Overall status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map(item => (
                  <tr
                    key={item.session_id}
                    className={selectedSessionId === item.session_id
                      ? 'validation-selected-row'
                      : ''}
                  >
                    <td>
                      <button
                        className="validation-session-select"
                        onClick={() => setSelectedSessionId(item.session_id)}
                      >
                        {item.session_id}
                      </button>
                    </td>
                    <td>
                      <span className={statusClass(item.mini_ookla_status)}>
                        {item.mini_ookla_status || 'pending'}
                      </span>
                    </td>
                    <td>
                      <span className={statusClass(item.iperf3_status)}>
                        {item.iperf3_status || 'pending'}
                      </span>
                    </td>
                    <td>
                      <span className={statusClass(item.status)}>
                        {item.status || 'unknown'}
                      </span>
                    </td>
                    <td>{item.created_at || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      {selectedSessionId && (
        <article className="panel validation-detail-panel">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">SESSION DETAILS</span>
              <h2>{selectedSessionId}</h2>
              <p>
                {session?.created_at || 'Creation time unavailable'}
                {session?.updated_at ? ` · Updated ${session.updated_at}` : ''}
              </p>
            </div>
            <span className={statusClass(status)}>{status}</span>
          </div>

          {detailLoading && !session && (
            <div className="graph-empty">Loading selected session...</div>
          )}
          {detailError && <div className="graph-empty">{detailError}</div>}

          {session && (
            <>
              <div className="validation-test-grid">
                <section className="validation-test-card">
                  <span className="panel-kicker">TEST 01</span>
                  <h3>Mini-Ookla</h3>
                  <span className={statusClass(session.mini_ookla_status)}>
                    {session.mini_ookla_status || 'pending'}
                  </span>
                  {session.mini_ookla_error && (
                    <p className="validation-error">{session.mini_ookla_error}</p>
                  )}
                  <div className="validation-test-metrics">
                    <div><span>Download</span><strong>{format(mini?.download_mbps)} Mbps</strong></div>
                    <div><span>Upload</span><strong>{format(mini?.upload_mbps)} Mbps</strong></div>
                    <div><span>Latency</span><strong>{format(mini?.latency_ms)} ms</strong></div>
                    <div><span>Saved result ID</span><strong>{mini?.id ?? '—'}</strong></div>
                  </div>
                  {!mini && <p className="validation-muted">No Mini-Ookla result is linked to this session yet.</p>}
                </section>

                <section className="validation-test-card">
                  <span className="panel-kicker">TEST 02</span>
                  <h3>iperf3</h3>
                  <span className={statusClass(session.iperf3_status)}>
                    {session.iperf3_status || 'pending'}
                  </span>
                  {session.iperf3_error && (
                    <p className="validation-error">{session.iperf3_error}</p>
                  )}
                  <div className="validation-test-metrics">
                    <div><span>Download</span><strong>{format(iperf?.download_mbps)} Mbps</strong></div>
                    <div><span>Upload</span><strong>{format(iperf?.upload_mbps)} Mbps</strong></div>
                    <div><span>Duration</span><strong>{format(iperf?.duration_sec)} s</strong></div>
                    <div><span>Saved result ID</span><strong>{iperf?.id ?? '—'}</strong></div>
                  </div>
                  {!iperf && <p className="validation-muted">No iperf3 result is linked to this session yet.</p>}
                </section>
              </div>

              <div className="validation-comparison">
                <div className="panel-heading">
                  <div>
                    <span className="panel-kicker">SIDE-BY-SIDE</span>
                    <h2>Throughput comparison</h2>
                    <p>Difference is iperf3 minus Mini-Ookla; negative values mean iperf3 measured lower.</p>
                  </div>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr><th>Metric</th><th>Mini-Ookla</th><th>iperf3</th><th>Difference</th><th>Mini-Ookla Difference (%)</th></tr>
                    </thead>
                    
<tbody>
  {comparisonRows.map(row => {
    const miniValue = mini?.[row.key]
    const iperfValue = iperf?.[row.key]

    const a = Number(miniValue)
    const b = Number(iperfValue)

    const comparable =
      miniValue !== null &&
      miniValue !== undefined &&
      miniValue !== '' &&
      iperfValue !== null &&
      iperfValue !== undefined &&
      iperfValue !== '' &&
      Number.isFinite(a) &&
      Number.isFinite(b)

    const percentageComparable =
      comparable && b !== 0

    const percentageDifference = percentageComparable
      ? ((a - b) / b) * 100
      : null

    return (
      <tr key={row.key}>
        <td>{row.label}</td>
        <td>{miniValue !== null && miniValue !== undefined && miniValue !== ''
          ? `${format(miniValue)} ${row.unit}`
          : '—'}</td>
        <td>{iperfValue !== null && iperfValue !== undefined && iperfValue !== ''
          ? `${format(iperfValue)} ${row.unit}`
          : '—'}</td>
        <td>
          {comparable
            ? `${(a - b).toFixed(2)} ${row.unit}`
            : 'Not available'}
        </td>
        <td>
          {percentageDifference !== null
            ? `${percentageDifference > 0 ? '+' : ''}${percentageDifference.toFixed(2)}%`
            : 'Not available'}
        </td>
      </tr>
    )
  })}
</tbody>

                  </table>
                </div>
                
<div className="throughput-charts-grid">
  <ThroughputComparisonChart
    title="Download Throughput"
    history={historicalSessions.map(item => ({
      session_id: item.session_id,
      mini: item.mini?.download_mbps,
      iperf: item.iperf?.download_mbps,
    }))}
  />

  <ThroughputComparisonChart
    title="Upload Throughput"
    history={historicalSessions.map(item => ({
      session_id: item.session_id,
      mini: item.mini?.upload_mbps,
      iperf: item.iperf?.upload_mbps,
    }))}
  />
</div>

                <p className="graph-footnote">
                  These tools may use different test methods and directions. Treat differences as
                  an observed comparison, not proof that one tool is more accurate.
                </p>
              </div>
            </>
          )}
        </article>
      )}
    </div>
  )
}


function App() {
  const [activePage, setActivePage] = useState('Network Visualiser')
  const [period, setPeriod] = useState('Last hour')
  const [query, setQuery] = useState('')
  const [isLive, setIsLive] = useState(true)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState('')

const [servers, setServers] = useState(initialServers)
const [serverStatusError, setServerStatusError] = useState('')


const [iperf3History, setIperf3History] = useState([])
const [iperf3Loading, setIperf3Loading] = useState(true)
const [iperf3Error, setIperf3Error] = useState('')



useEffect(() => {
  let cancelled = false
  let fetching = false

  async function fetchServers() {
    if (fetching) return
    fetching = true

    try {
      const response = await fetch('/api/servers')

      if (!response.ok) {
        throw new Error(`Server API returned HTTP ${response.status}`)
      }

      const data = await response.json()

      if (!Array.isArray(data.servers)) {
        throw new Error('Unexpected server API response format')
      }

      if (!cancelled) {
        setServers(
          initialServers.map((initial) => {
            const live = data.servers.find(
              (server) => server.server_id === initial.id
            )

            if (!live) {
              return {
                ...initial,
                status: 'Offline',
                latency: '—',
              }
            }

            return {
              ...initial,
              host: `${live.host}:${live.port}`,
              status: live.status === 'online' ? 'Online' : 'Offline',
              // The backend currently does not return probe latency.
              latency: '—',
            }
          })
        )

        setServerStatusError('')
      }
    } catch (error) {
      if (!cancelled) {
        setServerStatusError(
          error.message || 'Unable to fetch server status'
        )
      }
    } finally {
      fetching = false
    }
  }

  fetchServers()

  const intervalId = setInterval(fetchServers, 5000)

  return () => {
    cancelled = true
    clearInterval(intervalId)
  }
}, [])


useEffect(() => {
  let cancelled = false
  let fetching = false

  async function fetchResults() {
    if (fetching) return
    fetching = true

    try {
      const response = await fetch('/api/results')

      if (!response.ok) {
        throw new Error(`API returned HTTP ${response.status}`)
      }

      const data = await response.json()

      if (!Array.isArray(data)) {
        throw new Error('Unexpected API response format')
      }

      if (!cancelled) {
        setHistory(data)
        setApiError('')
      }
    } catch (error) {
      if (!cancelled) {
        setApiError(error.message || 'Unable to fetch results')
      }
    } finally {
      fetching = false

      if (!cancelled) {
        setLoading(false)
      }
    }
  }

  fetchResults()

  const intervalId = setInterval(fetchResults, 5000)

  return () => {
    cancelled = true
    clearInterval(intervalId)
  }
}, [])


useEffect(() => {
  let cancelled = false
  let fetching = false

  async function fetchIperf3Results() {
    if (fetching) return
    fetching = true

    try {
      const response = await fetch('/iperf3-api/results')

      if (!response.ok) {
        throw new Error(`API returned HTTP ${response.status}`)
      }

      const data = await response.json()

      if (!Array.isArray(data)) {
        throw new Error('Unexpected iperf3 API response format')
      }

      if (!cancelled) {
        setIperf3History(
          data
            .filter(record => record && record.id != null)
            .sort((a, b) => Number(b.id) - Number(a.id))
        )
        setIperf3Error('')
      }
    } catch (error) {
      if (!cancelled) {
        setIperf3Error(error.message || 'Unable to fetch iperf3 results')
      }
    } finally {
      fetching = false

      if (!cancelled) {
        setIperf3Loading(false)
      }
    }
  }

  fetchIperf3Results()
  const intervalId = setInterval(fetchIperf3Results, 5000)

  return () => {
    cancelled = true
    clearInterval(intervalId)
  }
}, [])




const sortedHistory = [...history].sort((a, b) => b.id - a.id)

const visibleHistory = sortedHistory.filter(item =>
  `${item.server_id} ${item.id}`.toLowerCase().includes(query.toLowerCase())
)

const latestResult = sortedHistory[0]
const showingComparison = activePage === 'Performance Comparison'
const showingHistory = activePage === 'Measurement History'
const showingIperf3 = activePage === 'iperf3 Performance'
const showingValidation = activePage === 'Validation Sessions'



  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">ST</div>
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
          <div className="health-row">
  <span className={`status-dot ${apiError ? 'red' : 'green'}`} />
  Flask API <span>{apiError ? 'Unreachable' : 'Connected'}</span>
</div>

{servers.map(server => (
  <div className="health-row" key={server.id}>
    <span className={`status-dot ${
      server.status === 'Online' ? 'green' :
      server.status === 'Offline' ? 'red' : ''
    }`} />
    {server.name} <span>{server.status}</span>
  </div>
))}
          <div className="sidebar-footer">NETWORK SPEED-TEST PLATFORM<br />Development environment</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> <strong>{activePage}</strong></div>
          <label className="search-box"><span>Q</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search servers or test history..." /></label>
          <div className="top-status"><span className="pulse-dot" /><div><strong>API connected</strong><small>Local development</small></div></div>
        </header>




<div className="page-content">
  {showingValidation ? (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="pulse-dot" /> VALIDATION WORKSPACE
          </div>
          <h1>Validation Sessions</h1>
          <p>
            Review paired Mini-Ookla and iperf3 measurements from the same session.
          </p>
        </div>
      </div>
      <ValidationSessionsPage />
    </>
  ) : showingHistory ? (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="pulse-dot" /> MEASUREMENT ARCHIVE
          </div>
          <h1>Measurement History</h1>
          <p>
            Search and review saved Mini-Ookla measurements.
          </p>
        </div>
        <span className="count-tag">
          {history.length} recorded tests
        </span>
      </div>

      <MeasurementHistoryPage
        history={history}
        query={query}
      />
    </>
  ) : showingIperf3 ? (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="pulse-dot" /> IPERF3 PERFORMANCE
          </div>
          <h1>iperf3 Performance</h1>
          <p>
            TCP throughput measurements, history, and server performance.
          </p>
        </div>
        <span className="count-tag">
          {iperf3History.length} recorded tests
        </span>
      </div>

      <Iperf3Page
        history={iperf3History}
        loading={iperf3Loading}
        error={iperf3Error}
      />
    </>
  ) : showingComparison ? (

    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="pulse-dot" /> PERFORMANCE ANALYTICS
          </div>
          <h1>Performance Comparison</h1>
          <p>
            Compare throughput and network quality across recorded measurements.
          </p>
        </div>
        <span className="count-tag">
  {history.length > 0
  ? `${history.length} recorded tests`
  : `${sampleResults.length} sample tests`}
</span>
      </div>

      <ComparisonPage history={history} />
    </>
  ) : (
    <>

          <div className="page-heading">
            <div><div className="eyebrow"><span className="pulse-dot" /> NETWORK OPERATIONS CENTER</div><h1>{activePage}</h1><p>Monitor your federated network and analyze performance across measurement servers.</p></div>
            <button className={`live-button ${isLive ? 'selected' : ''}`} onClick={() => setIsLive(!isLive)}><span className="pulse-dot" /> {isLive ? 'LIVE VIEW' : 'PAUSED'}</button>
          </div>

          <section className="metrics-grid">
            <MetricCard icon="NET" label="Configured servers" value="3" unit="" tone="cyan" foot={`${servers.filter(server => server.status === 'Online').length} servers online`} />

<MetricCard
  icon="↓"
  label="Latest download"
  value={latestResult ? Number(latestResult.download_mbps).toFixed(2) : '—'}
  unit=" Mbps"
  tone="blue"
  foot={loading ? 'Loading...' : apiError ? 'API unavailable' : 'Latest saved result'}
/>


<MetricCard
  icon="↑"
  label="Latest upload"
  value={latestResult ? Number(latestResult.upload_mbps).toFixed(2) : '—'}
  unit=" Mbps"
  tone="purple"
  foot={loading ? 'Loading...' : apiError ? 'API unavailable' : 'Latest saved result'}
/>


<MetricCard
  icon="MS"
  label="Latest latency"
  value={latestResult ? Number(latestResult.latency_ms).toFixed(2) : '—'}
  unit=" ms"
  tone="amber"
  foot={loading ? 'Loading...' : apiError ? 'API unavailable' : 'Latest saved result'}
/>

          </section>

          <section className="primary-grid">
            <article className="panel topology-panel">
              <div className="panel-heading"><div><span className="panel-kicker">FEDERATION MAP</span><h2>Network topology</h2><p>Measurement server connectivity</p></div><span className={`live-tag ${isLive ? '' : 'paused'}`}><span className="pulse-dot" />{isLive ? 'MONITORING' : 'PAUSED'}</span></div>

              <div className="topology-canvas">
                <div className="topology-glow" />
                <svg className="connection-lines" viewBox="0 0 700 370" preserveAspectRatio="none">
                  <defs><linearGradient id="flow" x1="0" y1="0" x2="1" y2="0"><stop stopColor="#0debd1" /><stop offset="1" stopColor="#4777ff" /></linearGradient></defs>
                  {[[160,180,470,70],[160,180,470,185],[160,180,470,300]].map((line, i) => <g key={i}><path d={`M ${line[0]} ${line[1]} C 280 ${line[1]}, 340 ${line[3]}, ${line[2]} ${line[3]}`} className={`connection ${
  servers[i]?.status === 'Online' ? 'connection-active' : ''
}`} /><circle r="4" className={
  servers[i]?.status === 'Online' ? 'flow-dot' : 'idle-dot'
}><animateMotion dur={servers[i]?.status === 'Online' ? '2.5s' : '6s'} repeatCount="indefinite" path={`M ${line[0]} ${line[1]} C 280 ${line[1]}, 340 ${line[3]}, ${line[2]} ${line[3]}`} /></circle></g>)}
                </svg>

                <div className="node client-node"><div className="node-orb">PC</div><strong>Your client</strong><small>HP · Windows</small></div>

{servers.map((server, i) => (
  <div
    key={server.id}
    className={`node server-node server-${i + 1}`}
  >
    <div
      className={`node-orb ${
        server.status === 'Online' ? 'online' : 'offline'
      }`}
    >
      SRV
    </div>

    <div className="node-copy">
      <strong>{server.name}</strong>
      <small>{server.host}</small>
      <span
        className={
          server.status === 'Online' ? 'online-text' : 'offline-text'
        }
      >
        <i />
        {server.status} · {server.latency}
      </span>
    </div>
  </div>
))}

                <div className="topology-legend"><span><i className="legend-line active-line" /> Verified probe</span><span><i className="legend-line idle-line" /> Unverified connection</span><span><i className="legend-dot" /> Data-flow animation (visual demo)</span></div>
              </div>
            </article>

            <article className="panel performance-panel">
              
<div className="panel-heading">
  <div>
    <span className="panel-kicker">PERFORMANCE TELEMETRY</span>
    <h2>Throughput overview</h2>
    <p>Historical records · not a live stream</p>
  </div>
</div>


<div className="chart-stats">
  <div>
    <span className="chart-legend cyan-legend" />
    Download
    <strong>
      {latestResult ? Number(latestResult.download_mbps).toFixed(2) : '—'}
      <small> Mbps</small>
    </strong>
  </div>
  <div>
    <span className="chart-legend purple-legend" />
    Upload
    <strong>
      {latestResult ? Number(latestResult.upload_mbps).toFixed(2) : '—'}
      <small> Mbps</small>
    </strong>
  </div>
</div>

              <div className="chart-wrap">
              <LineChart history={sortedHistory} />
              </div>
              <div className="chart-xlabels"><span>Earlier</span><span>Recent</span><span>Latest saved result</span></div>

<div className="chart-note">
  <span className={`status-dot ${apiError ? 'red' : 'green'}`} />
  {loading
    ? 'Loading measurement history...'
    : apiError
      ? `Unable to load history: ${apiError}`
      : 'Showing saved measurement history; this is not a live stream.'}
</div>

            </article>
          </section>

          <footer className="page-footer"><span>SpeedTest Network <b>·</b> Mini-Ookla federation project</span><span><i className="status-dot green" /> Dashboard UI preview <b>·</b> API-backed measurement history</span></footer>
                  </>
        )}
        </div>
      </main>
    </div>
  )
}

export default App












