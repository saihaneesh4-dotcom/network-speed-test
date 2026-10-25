import { useEffect, useState } from 'react'
import './App.css'
import { sampleResults } from "./sampledata";

const initialServers = [
  { id: 'server_01', name: 'Server A', host: '10.56.66.133:5001', status: 'Online', latency: '10.6 ms' },
  { id: 'server_02', name: 'Server B', host: '10.140.251.133:5002', status: 'Offline', latency: '—' },
  { id: 'server_03', name: 'Server C', host: '10.140.251.133:5003', status: 'Offline', latency: '—' },
]




const navigation = [
  {
    label: 'Network Visualiser',
    icon: '⌘',
    sub: 'Latest test & network overview',
  },
  {
    label: 'Performance Comparison',
    icon: '↗',
    sub: 'Compare network measurements',
  },
  {
    label: 'iperf3 Performance',
    icon: '↗',
    sub: 'TCP throughput & measurement history',
  },

{
  label: 'Measurement History',
  icon: '◷',
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
                <span className="legend-download">● Download</span>
                <span className="legend-upload">● Upload</span>
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
            <span className="legend-latency">● Latency scale</span>
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
            <span className="legend-download">■ Download</span>
            <span className="legend-upload">■ Upload</span>
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
    </div>
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
          icon="✓"
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
              <span className="legend-download">● Download</span>
              <span className="legend-upload">● Upload</span>
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
  const records = [...history]
    .filter(record => record && record.id != null)
    .sort((a, b) => Number(b.id) - Number(a.id))
    .filter(record =>
      `${record.id} ${record.server_id ?? ''} ${record.timestamp ?? ''}`
        .toLowerCase()
        .includes(query.toLowerCase())
    )

  const format = (value, decimals = 2) => {
    if (value === null || value === undefined || value === '') {
      return '—'
    }

    const number = Number(value)
    return Number.isFinite(number) ? number.toFixed(decimals) : '—'
  }

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
          value={format(history.length
            ? [...history].sort((a, b) => Number(b.id) - Number(a.id))[0]?.download_mbps
            : null)}
          unit=" Mbps"
          tone="blue"
          foot="Latest saved record"
        />

        <MetricCard
          icon="↑"
          label="Latest upload"
          value={format(history.length
            ? [...history].sort((a, b) => Number(b.id) - Number(a.id))[0]?.upload_mbps
            : null)}
          unit=" Mbps"
          tone="purple"
          foot="Latest saved record"
        />

        <MetricCard
          icon="◷"
          label="Matching records"
          value={String(records.length)}
          unit=""
          tone="amber"
          foot="Based on search filter"
        />
      </section>

      <article className="panel history-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">MEASUREMENT ARCHIVE</span>
            <h2>Complete Measurement History</h2>
            <p>Saved Mini-Ookla records, newest first</p>
          </div>
          <span className="count-tag">{records.length} records</span>
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
              {records.map(record => (
                <tr key={record.id}>
                  <td className="muted-cell">#{record.id}</td>
                  <td>
                    {record.server_id || 'Unknown'}
                  </td>
                  <td className="cyan-cell">
                    {format(record.download_mbps)} Mbps
                  </td>
                  <td className="purple-cell">
                    {format(record.upload_mbps)} Mbps
                  </td>
                  <td>{format(record.latency_ms)} ms</td>
                  <td>{format(record.jitter_ms ?? record.jitter)} ms</td>
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

        {records.length === 0 && (
          <div className="graph-empty">
            No matching measurements found.
          </div>
        )}

        <div className="table-foot">
          Showing saved backend measurements. Missing values are displayed
          as unavailable rather than treated as zero.
        </div>
      </article>
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
  {showingHistory ? (
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
            <MetricCard icon="◈" label="Configured servers" value="3" unit="" tone="cyan" foot="1 probe verified" />

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
  icon="ϟ"
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

                <div className="node client-node"><div className="node-orb">⌘</div><strong>Your client</strong><small>HP · Windows</small></div>

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
      ▤
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
              <div className="panel-heading"><div><span className="panel-kicker">PERFORMANCE TELEMETRY</span><h2>Throughput overview</h2><p>Historical records · not a live stream</p></div><select value={period} onChange={e => setPeriod(e.target.value)}><option>Last hour</option><option>24 hours</option><option>7 days</option></select></div>

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
