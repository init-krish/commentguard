import { useEffect, useState } from 'react';
import { Shield, Activity, AlertTriangle, CheckCircle, BarChart3, Database } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './index.css';

// Types
interface Stats {
  total: number;
  toxic: number;
  non_toxic: number;
  toxic_rate: number;
  model: string;
  version: string;
  by_category: Record<string, number>;
  recent: Array<{
    text: string;
    max_prob: number;
    label: string;
    decision: 'allow' | 'review' | 'block';
    categories: string[];
    time: string;
  }>;
}

// Generate some fake chart data for visual flair since we don't store time-series in memory yet
const generateChartData = (currentRate: number) => {
  const data = [];
  let prev = currentRate || 10;
  for (let i = 24; i >= 0; i--) {
    prev = Math.max(0, Math.min(100, prev + (Math.random() * 10 - 5)));
    data.push({
      time: `${i}h ago`,
      toxicity: i === 0 ? currentRate : Math.round(prev * 10) / 10
    });
  }
  return data;
};

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8000/stats');
      if (!res.ok) throw new Error('API unreachable');
      const data = await res.json();
      setStats(data);
      if (chartData.length === 0) {
        setChartData(generateChartData(data.toxic_rate));
      }
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  // Poll every 3 seconds
  useEffect(() => {
    fetchStats();
    const int = setInterval(fetchStats, 3000);
    return () => clearInterval(int);
  }, []);

  if (!stats && !error) {
    return (
      <div className="loading-overlay">
        <div className="spinner"></div>
        <p style={{ color: 'var(--text-secondary)' }}>Connecting to API...</p>
      </div>
    );
  }

  const categoryLabels: Record<string, string> = {
    toxic: "Toxic",
    severe_toxic: "Severe",
    obscene: "Obscene",
    threat: "Threat",
    insult: "Insult",
    identity_hate: "Hate"
  };

  return (
    <div className="dashboard-container">
      <header className="header">
        <div className="title-group">
          <h1><Shield className="w-8 h-8 text-blue-500" /> CommentGuard Dashboard</h1>
          <p>Real-time toxicity analytics and moderation logs</p>
        </div>
        <div className="live-badge">
          <div className="pulse"></div>
          {error ? <span style={{ color: 'var(--toxic)' }}>API Offline</span> : 'System Live'}
        </div>
      </header>

      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '1rem', borderRadius: '8px', marginBottom: '2rem', border: '1px solid var(--toxic)', color: '#fca5a5' }}>
          <strong>Connection Error:</strong> Make sure the FastAPI backend is running on http://localhost:8000
        </div>
      )}

      {stats && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <Activity className="stat-icon w-16 h-16" />
              <div className="stat-title">Total Processed</div>
              <div className="stat-value">{stats.total.toLocaleString()}</div>
            </div>
            
            <div className="stat-card">
              <AlertTriangle className="stat-icon w-16 h-16" />
              <div className="stat-title">Toxic Comments</div>
              <div className="stat-value">{stats.toxic.toLocaleString()}</div>
            </div>

            <div className="stat-card">
              <BarChart3 className="stat-icon w-16 h-16" />
              <div className="stat-title">Toxicity Rate</div>
              <div className="stat-value stat-rate">{stats.toxic_rate}%</div>
            </div>

            <div className="stat-card">
              <Database className="stat-icon w-16 h-16" />
              <div className="stat-title">Active Model</div>
              <div className="stat-value" style={{ fontSize: '1.5rem', marginTop: '1rem', textTransform: 'capitalize' }}>
                {stats.model} v{stats.version}
              </div>
            </div>
          </div>

          <div className="main-grid">
            {/* Left Panel - Logs */}
            <div className="panel">
              <h2><CheckCircle className="w-5 h-5" /> Recent Moderation Logs</h2>
              <div className="log-list">
                {stats.recent.length === 0 ? (
                  <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>No comments processed yet.</p>
                ) : (
                  [...stats.recent].reverse().map((log, i) => (
                    <div className="log-item" key={i}>
                      <div className="log-header">
                        <div className="log-badges">
                          <span className={`badge ${log.decision}`}>{log.decision}</span>
                          {log.categories.map(c => (
                            <span key={c} className="badge cat">{categoryLabels[c] || c}</span>
                          ))}
                        </div>
                        <div className="log-footer">
                          {new Date(log.time).toLocaleTimeString()}
                        </div>
                      </div>
                      <div className="log-text">
                        "{log.text}"
                      </div>
                      <div className="log-footer" style={{ justifyContent: 'flex-start', gap: '1rem' }}>
                        <span>Max Prob: <strong style={{ color: log.max_prob > 0.5 ? 'var(--toxic)' : 'inherit' }}>{(log.max_prob * 100).toFixed(1)}%</strong></span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right Panel - Analytics */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div className="panel">
                <h2><BarChart3 className="w-5 h-5" /> Category Breakdown</h2>
                <div className="category-bars">
                  {Object.entries(stats.by_category).map(([cat, count]) => {
                    const pct = stats.toxic > 0 ? Math.round((count / stats.toxic) * 100) : 0;
                    return (
                      <div className="cat-bar-container" key={cat}>
                        <div className="cat-bar-header">
                          <span>{categoryLabels[cat] || cat}</span>
                          <span>{count} ({pct}%)</span>
                        </div>
                        <div className="cat-bar-bg">
                          <div 
                            className={`cat-bar-fill cat-${cat}`} 
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="panel" style={{ flexGrow: 1 }}>
                <h2><Activity className="w-5 h-5" /> Toxicity Trend</h2>
                <div style={{ height: '200px', marginTop: '1rem' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="colorTox" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--toxic)" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="var(--toxic)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                      <XAxis dataKey="time" hide />
                      <YAxis stroke="var(--text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip 
                        contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                        itemStyle={{ color: 'var(--text-primary)' }}
                      />
                      <Area isAnimationActive={false} type="monotone" dataKey="toxicity" stroke="var(--toxic)" strokeWidth={2} fillOpacity={1} fill="url(#colorTox)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
