import React, { useState, useEffect, useMemo, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './App.css';

const API_BASE = 'http://localhost:8001';

const STATUS_ICONS = {
  'Submitted': '⏳',
};

function timeAgo(dateString) {
  const diffMs = Date.now() - new Date(dateString).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [toast, onClose]);

  if (!toast) return null;

  return (
    <div className={`toast toast-${toast.type}`} role="status">
      <span className="toast-icon">
        {toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : 'ℹ'}
      </span>
      <span className="toast-message">{toast.message}</span>
      <button className="toast-close" onClick={onClose} aria-label="Dismiss">
        &times;
      </button>
    </div>
  );
}

function StatCard({ label, value, tone }) {
  return (
    <div className={`stat-card stat-${tone}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function MiniBarChart({ title, data, accent = '#2563eb' }) {
  const maxValue = Math.max(1, ...data.map((d) => d.value));
  const niceMax = Math.ceil(maxValue * 1.2) || 1;

  return (
    <div className="chart-card">
      <h4 className="chart-title">{title}</h4>
      {data.length === 0 ? (
        <p className="chart-empty">No data yet.</p>
      ) : (
        <div className="chart-body">
          {data.map((d) => {
            const pct = (d.value / niceMax) * 100;
            return (
              <div key={d.label} className="chart-row">
                <div className="chart-label" title={d.label}>
                  {d.label}
                </div>
                <div className="chart-track">
                  <div
                    className="chart-fill"
                    style={{ width: `${pct}%`, background: accent }}
                  />
                </div>
                <div className="chart-value">{d.value}</div>
                <div className="chart-tooltip">
                  {d.label}: {d.value} request{d.value !== 1 ? 's' : ''}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="rfc-card skeleton-card">
      <div className="skeleton-line skeleton-title" />
      <div className="skeleton-line skeleton-sub" />
      <div className="skeleton-badges">
        <div className="skeleton-badge" />
        <div className="skeleton-badge" />
      </div>
      <div className="skeleton-line skeleton-date" />
    </div>
  );
}

// Display order for flag groups. Flags raised by multiple agents for the
// same underlying concern are merged server-side, so grouping is by
// category (not by agent) with a "raised by" tag listing every contributor.
const CATEGORY_ORDER = [
  'Access/Permissions', 'Testing', 'Rollback/Recovery',
  'Communication/SLA', 'Compliance/Security', 'Infrastructure', 'Other',
];
const SEV_ORDER = { 'Must-fix': 0, 'Should-fix': 1, 'Nice-to-have': 2 };

// Agents append a machine-readable "FLAGS: [...]" block to their prose. Those
// flags are already shown by <FlagsPanel>, so strip the raw block from any text
// rendered to the user (handles legacy records that stored the block inline).
function stripFlags(text) {
  if (typeof text !== 'string') return text;
  const idx = text.lastIndexOf('FLAGS:');
  return idx === -1 ? text : text.slice(0, idx).trimEnd();
}

// A CAB deliberation log entry that is the required-changes summary. The styled
// <FlagsPanel> already renders those, so this entry is filtered out of the log
// stream to avoid showing "Required Changes & Recommendations" twice.
function isFlagsBlock(log) {
  return typeof log === 'string' && log.includes('REQUIRED CHANGES & RECOMMENDATIONS');
}

function FlagsPanel({ flags }) {
  const list = Array.isArray(flags) ? flags : [];
  const counts = list.reduce((acc, f) => {
    acc[f.severity] = (acc[f.severity] || 0) + 1;
    return acc;
  }, {});
  return (
    <div className="flags-panel">
      <h3>🚩 Required Changes & Recommendations</h3>
      {list.length === 0 ? (
        <p className="flags-empty">No required changes flagged.</p>
      ) : (
        <>
          <div className="flags-summary">
            {counts['Must-fix'] > 0 && (
              <span className="flags-chip chip-mustfix">{counts['Must-fix']} Must-fix</span>
            )}
            {counts['Should-fix'] > 0 && (
              <span className="flags-chip chip-shouldfix">{counts['Should-fix']} Should-fix</span>
            )}
            {counts['Nice-to-have'] > 0 && (
              <span className="flags-chip chip-nice">{counts['Nice-to-have']} Nice-to-have</span>
            )}
          </div>
          {CATEGORY_ORDER.map((category) => {
            const group = list
              .filter((f) => f.category === category)
              .sort(
                (a, b) =>
                  (SEV_ORDER[a.severity] ?? 3) - (SEV_ORDER[b.severity] ?? 3)
              );
            if (group.length === 0) return null;
            return (
              <div key={category} className="flag-group">
                <h4>{category}</h4>
                {group.map((f, i) => (
                  <div key={i} className="flag-item">
                    <div className="flag-head">
                      <span
                        className={`sev-badge sev-${(f.severity || '').replace(
                          /[^a-zA-Z]/g,
                          ''
                        )}`}
                      >
                        {f.severity}
                      </span>
                      <span className="flag-element">{f.affected_element}</span>
                    </div>
                    <p className="flag-rec">{f.recommendation}</p>
                    {f.raised_by && (
                      <p className="flag-raised-by">Raised by: {f.raised_by}</p>
                    )}
                  </div>
                ))}
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}

// Color/icon identity per CAB agent, used to turn the deliberation transcript
// into distinct colored cards instead of a wall of uniform paragraphs.
const AGENT_META = {
  Infrastructure: { color: '#2563eb', icon: '🖥️', label: 'Infrastructure Specialist' },
  Application: { color: '#7c3aed', icon: '💻', label: 'Application Specialist' },
  Business: { color: '#059669', icon: '💼', label: 'Business & Service Owner' },
  Security: { color: '#dc2626', icon: '🛡️', label: 'Security & Compliance Officer' },
  Chair: { color: '#b45309', icon: '📋', label: 'Change Manager (Chair)' },
};

// Backend log entries look like "🔍 INFRASTRUCTURE SPECIALIST:\n<opinion>" or
// "📋 CHANGE MANAGER (SYNTHESIS):\n<synthesis>". Extract which agent it is and
// the body text so each can be rendered as its own colored card.
function parseAgentLog(log) {
  const text = stripFlags(log || '').trim();
  const match = text.match(/^(?:🔍|📋)\s*([^:]+):\s*([\s\S]*)$/);
  const rawName = match ? match[1].toUpperCase() : '';
  const body = match ? match[2].trim() : text;

  let key = 'Chair';
  if (rawName.includes('INFRASTRUCTURE')) key = 'Infrastructure';
  else if (rawName.includes('APPLICATION')) key = 'Application';
  else if (rawName.includes('BUSINESS')) key = 'Business';
  else if (rawName.includes('SECURITY')) key = 'Security';

  return {
    meta: AGENT_META[key],
    body,
    isSynthesis: rawName.includes('SYNTHESIS'),
  };
}

const DECISION_META = {
  'Approved': { color: '#15803d', bg: '#dcfce7', icon: '✓' },
  'Rejected': { color: '#b91c1c', bg: '#fee2e2', icon: '✕' },
  'Conditional Approval': { color: '#b45309', bg: '#fef3c7', icon: '△' },
  'Pending Review': { color: '#475569', bg: '#f1f5f9', icon: '…' },
};

function DecisionBadge({ decision }) {
  const meta = DECISION_META[decision] || DECISION_META['Pending Review'];
  return (
    <span className="decision-badge" style={{ color: meta.color, background: meta.bg }}>
      <span className="decision-badge-icon">{meta.icon}</span> {decision}
    </span>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState('list');
  const [rfcs, setRfcs] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const [selectedRfc, setSelectedRfc] = useState(null);
  const [cabSession, setCabSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('All');
  const [filterStatus, setFilterStatus] = useState('All');
  const [visibleLogCount, setVisibleLogCount] = useState(0);
  const [notifOpen, setNotifOpen] = useState(false);
  const [cabResultTab, setCabResultTab] = useState('deliberation');
  const revealTimer = useRef(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    business_justification: '',
    implementation_plan: '',
    test_cases: '',
    back_out_plan: '',
    affected_systems: '',
    estimated_downtime_hours: 0,
    requestor_name: '',
  });

  useEffect(() => {
    fetchRfcList();
  }, []);

  useEffect(() => {
    return () => clearInterval(revealTimer.current);
  }, []);

  const showToast = (message, type = 'info') => setToast({ message, type });

  const fetchRfcList = async () => {
    setListLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/rfc-list`);
      setRfcs(response.data.rfcs);
    } catch (error) {
      showToast('Unable to reach the RFC service. Confirm the backend is running.', 'error');
    } finally {
      setListLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmitRfc = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        affected_systems: formData.affected_systems
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        estimated_downtime_hours: parseFloat(formData.estimated_downtime_hours),
      };

      const response = await axios.post(`${API_BASE}/rfc/submit`, payload);
      showToast(`RFC submitted successfully — ${response.data.rfc_number}`, 'success');
      setFormData({
        title: '',
        description: '',
        business_justification: '',
        implementation_plan: '',
        test_cases: '',
        back_out_plan: '',
        affected_systems: '',
        estimated_downtime_hours: 0,
        requestor_name: '',
      });
      setActiveTab('list');
      fetchRfcList();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Submission failed. Please review the form and try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleViewRfc = async (rfc_id) => {
    try {
      const response = await axios.get(`${API_BASE}/rfc/${rfc_id}`);
      setSelectedRfc(response.data);
      setCabSession(null);
      setVisibleLogCount(0);
      setCabResultTab(response.data.cab_decision ? 'decision' : 'deliberation');
    } catch (error) {
      showToast('Unable to load RFC details.', 'error');
    }
  };

  const handleTriggerCab = async (rfc_id) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/rfc/${rfc_id}/trigger-cab`);
      setCabSession(response.data);
      setVisibleLogCount(0);
      setCabResultTab('deliberation');

      const total = (response.data.agent_logs || []).filter((l) => !isFlagsBlock(l)).length;
      let count = 0;
      clearInterval(revealTimer.current);
      revealTimer.current = setInterval(() => {
        count += 1;
        setVisibleLogCount(count);
        if (count >= total) clearInterval(revealTimer.current);
      }, 550);
    } catch (error) {
      showToast(`CAB session failed: ${error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = useMemo(() => {
    const total = rfcs.length;
    const autoApproved = rfcs.filter((r) => /auto-approved/i.test(r.status)).length;
    const emergency = rfcs.filter((r) => r.change_type === 'Emergency').length;
    const pending = rfcs.filter(
      (r) => !/auto-approved/i.test(r.status) && !/approved|rejected/i.test(r.status)
    ).length;
    return { total, autoApproved, emergency, pending };
  }, [rfcs]);

  const changeTypes = useMemo(
    () => ['All', ...Array.from(new Set(rfcs.map((r) => r.change_type)))],
    [rfcs]
  );
  const statuses = useMemo(
    () => ['All', ...Array.from(new Set(rfcs.map((r) => r.status)))],
    [rfcs]
  );

  const typeChartData = useMemo(() => {
    const counts = {};
    rfcs.forEach((r) => {
      counts[r.change_type] = (counts[r.change_type] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
  }, [rfcs]);

  const statusChartData = useMemo(() => {
    const counts = {};
    rfcs.forEach((r) => {
      counts[r.status] = (counts[r.status] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
  }, [rfcs]);

  const recentActivity = useMemo(
    () =>
      [...rfcs]
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 6),
    [rfcs]
  );

  const filteredRfcs = useMemo(() => {
    return rfcs.filter((r) => {
      const matchesQuery =
        !searchQuery ||
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.rfc_number.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesType = filterType === 'All' || r.change_type === filterType;
      const matchesStatus = filterStatus === 'All' || r.status === filterStatus;
      return matchesQuery && matchesType && matchesStatus;
    });
  }, [rfcs, searchQuery, filterType, filterStatus]);

  // Deliberation log entries minus the required-changes summary (shown via FlagsPanel)
  const visibleAgentLogs = (cabSession?.agent_logs || []).filter((l) => !isFlagsBlock(l));

  return (
    <div className="app">
      <Toast toast={toast} onClose={() => setToast(null)} />

      <header className="header">
        <div className="header-brand">
          <div className="brand-mark">CAB</div>
          <div>
            <h1>Change Advisory Board Platform</h1>
            <p>AI-assisted RFC classification, routing, and deliberation</p>
          </div>
        </div>
        <div className="header-actions">
          <div className="notif-wrapper">
            {notifOpen && (
              <div className="dropdown-backdrop" onClick={() => setNotifOpen(false)} />
            )}
            <button
              className="icon-btn"
              onClick={() => setNotifOpen((o) => !o)}
              aria-label="Recent activity"
            >
              🔔
              {recentActivity.length > 0 && <span className="notif-dot" />}
            </button>
            {notifOpen && (
              <div className="notif-dropdown">
                <div className="notif-header">Recent Activity</div>
                {recentActivity.length === 0 ? (
                  <div className="notif-empty">No activity yet.</div>
                ) : (
                  recentActivity.map((r) => (
                    <div
                      key={r.id}
                      className="notif-item"
                      onClick={() => {
                        handleViewRfc(r.id);
                        setActiveTab('detail');
                        setNotifOpen(false);
                      }}
                    >
                      <div className="notif-item-title">{r.title}</div>
                      <div className="notif-item-meta">
                        <span className="badge status-generic">{r.status}</span>
                        <span className="notif-time">{timeAgo(r.created_at)}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <nav className="tabs">
        <button
          className={`tab-btn ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          RFC Register
        </button>
        <button
          className={`tab-btn ${activeTab === 'submit' ? 'active' : ''}`}
          onClick={() => setActiveTab('submit')}
        >
          Submit Change Request
        </button>
      </nav>

      {activeTab === 'list' && (
        <div className="content fade-in">
          <div className="stats-row">
            <StatCard label="Total RFCs" value={stats.total} tone="neutral" />
            <StatCard label="Auto-Approved" value={stats.autoApproved} tone="success" />
            <StatCard label="Pending Review" value={stats.pending} tone="warning" />
            <StatCard label="Emergency Changes" value={stats.emergency} tone="danger" />
          </div>

          <div className="charts-row">
            <MiniBarChart title="RFCs by Change Type" data={typeChartData} accent="#2563eb" />
            <MiniBarChart title="RFCs by Status" data={statusChartData} accent="#2563eb" />
          </div>

          <div className="rfc-list">
            <div className="list-header">
              <h2>Change Requests</h2>
              <div className="filters">
                <input
                  type="text"
                  className="search-input"
                  placeholder="Search by title or RFC number..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                  {changeTypes.map((t) => (
                    <option key={t} value={t}>
                      {t === 'All' ? 'All Types' : t}
                    </option>
                  ))}
                </select>
                <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                  {statuses.map((s) => (
                    <option key={s} value={s}>
                      {s === 'All' ? 'All Statuses' : s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {listLoading ? (
              <div className="rfc-cards">
                {Array.from({ length: 4 }).map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            ) : filteredRfcs.length === 0 ? (
              <div className="empty-state">
                <p>No change requests match your current filters.</p>
              </div>
            ) : (
              <div className="rfc-cards">
                {filteredRfcs.map((rfc) => (
                  <div
                    key={rfc.id}
                    className="rfc-card"
                    onClick={() => {
                      handleViewRfc(rfc.id);
                      setActiveTab('detail');
                    }}
                  >
                    <h3>{rfc.title}</h3>
                    <p className="rfc-number">{rfc.rfc_number}</p>
                    <div className="rfc-meta">
                      <span className={`badge type-${rfc.change_type.replace(/\s/g, '')}`}>
                        {rfc.change_type}
                      </span>
                      <span className="badge status-generic">
                        {STATUS_ICONS[rfc.status] || ''} {rfc.status}
                      </span>
                    </div>
                    <p className="rfc-date">{timeAgo(rfc.created_at)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'submit' && (
        <div className="content fade-in">
          <div className="submit-form">
            <h2>Submit New Change Request</h2>
            <p className="form-subtitle">
              Fields marked with an asterisk are required for classification and routing.
            </p>
            <form onSubmit={handleSubmitRfc}>
              <div className="form-group">
                <label>RFC Title *</label>
                <input
                  type="text"
                  name="title"
                  value={formData.title}
                  onChange={handleInputChange}
                  required
                  placeholder="e.g., Deploy new payment service"
                />
              </div>

              <div className="form-group">
                <label>Description *</label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  required
                  placeholder="What change are we making and why?"
                  rows="4"
                />
              </div>

              <div className="form-group">
                <label>Business Justification *</label>
                <textarea
                  name="business_justification"
                  value={formData.business_justification}
                  onChange={handleInputChange}
                  required
                  placeholder="Why is this change business critical?"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Affected Systems * (comma-separated)</label>
                <input
                  type="text"
                  name="affected_systems"
                  value={formData.affected_systems}
                  onChange={handleInputChange}
                  required
                  placeholder="e.g., Database, API Gateway, Mobile App"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Estimated Downtime (hours)</label>
                  <input
                    type="number"
                    name="estimated_downtime_hours"
                    value={formData.estimated_downtime_hours}
                    onChange={handleInputChange}
                    step="0.5"
                    min="0"
                  />
                </div>

                <div className="form-group">
                  <label>Requestor Name *</label>
                  <input
                    type="text"
                    name="requestor_name"
                    value={formData.requestor_name}
                    onChange={handleInputChange}
                    required
                    placeholder="Your name"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Implementation Plan</label>
                <textarea
                  name="implementation_plan"
                  value={formData.implementation_plan}
                  onChange={handleInputChange}
                  placeholder="Step-by-step implementation details"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Test Cases</label>
                <textarea
                  name="test_cases"
                  value={formData.test_cases}
                  onChange={handleInputChange}
                  placeholder="What testing has been done?"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Back-Out Plan</label>
                <textarea
                  name="back_out_plan"
                  value={formData.back_out_plan}
                  onChange={handleInputChange}
                  placeholder="How will we rollback if needed?"
                  rows="3"
                />
              </div>

              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? (
                  <span className="btn-spinner-wrap">
                    <span className="btn-spinner" /> Submitting...
                  </span>
                ) : (
                  'Submit Change Request'
                )}
              </button>
            </form>
          </div>
        </div>
      )}

      {activeTab === 'detail' && selectedRfc && (
        <div className="content fade-in">
          <div className="rfc-detail">
            <button className="btn-back" onClick={() => setActiveTab('list')}>
              &larr; Back to Register
            </button>

            <h2>{selectedRfc.title}</h2>
            <div className="detail-meta">
              <div className="meta-item">
                <strong>RFC Number</strong> {selectedRfc.rfc_number}
              </div>
              <div className="meta-item">
                <strong>Type</strong>
                <span className={`badge type-${selectedRfc.change_type.replace(/\s/g, '')}`}>
                  {selectedRfc.change_type}
                </span>
              </div>
              <div className="meta-item">
                <strong>Status</strong>
                <span className="badge status-generic">{selectedRfc.status}</span>
              </div>
              <div className="meta-item">
                <strong>Impact</strong> {selectedRfc.impact}
              </div>
              <div className="meta-item">
                <strong>Priority</strong> {selectedRfc.priority}
              </div>
              {selectedRfc.risk_level && (
                <div className="meta-item">
                  <strong>Risk Level</strong>
                  <div className="risk-meter">
                    <div
                      className="risk-meter-fill"
                      style={{ width: `${(selectedRfc.risk_level / 5) * 100}%` }}
                    />
                  </div>
                  <span>{selectedRfc.risk_level} / 5</span>
                </div>
              )}
            </div>

            <div className="detail-section">
              <h3>Description</h3>
              <p>{selectedRfc.description}</p>
            </div>

            {selectedRfc.business_justification && (
              <div className="detail-section">
                <h3>Business Justification</h3>
                <p>{selectedRfc.business_justification}</p>
              </div>
            )}

            {selectedRfc.implementation_plan && (
              <div className="detail-section">
                <h3>Implementation Plan</h3>
                <p>{selectedRfc.implementation_plan}</p>
              </div>
            )}

            {selectedRfc.test_cases && (
              <div className="detail-section">
                <h3>Test Cases &amp; Results</h3>
                <p>{selectedRfc.test_cases}</p>
              </div>
            )}

            {selectedRfc.back_out_plan && (
              <div className="detail-section">
                <h3>Rollback / Back-Out Plan</h3>
                <p>{selectedRfc.back_out_plan}</p>
              </div>
            )}

            {selectedRfc.auto_approved && (
              <div className="detail-section alert alert-success">
                <strong>Auto-Approved:</strong> This RFC matches a Standard Change
                Catalogue entry and was approved automatically.
              </div>
            )}

            {!selectedRfc.auto_approved &&
              !selectedRfc.cab_decision &&
              selectedRfc.change_type !== 'Standard' && (
                <button
                  className="btn-primary"
                  onClick={() => handleTriggerCab(selectedRfc.id)}
                  disabled={loading || cabSession}
                >
                  {loading ? (
                    <span className="btn-spinner-wrap">
                      <span className="btn-spinner" /> Convening CAB Session...
                    </span>
                  ) : (
                    'Trigger AI CAB Review'
                  )}
                </button>
              )}

            {(cabSession || selectedRfc.cab_decision) && (() => {
              const decision = cabSession ? cabSession.cab_decision : selectedRfc.cab_decision;
              const reasoning = cabSession ? cabSession.cab_reasoning : selectedRfc.cab_reasoning;
              const flags = cabSession ? cabSession.cab_flags : selectedRfc.cab_flags;
              const flagCount = Array.isArray(flags) ? flags.length : 0;

              return (
                <div className="cab-session">
                  <div className="cab-tabs">
                    {cabSession && (
                      <button
                        className={`cab-tab-btn ${cabResultTab === 'deliberation' ? 'active' : ''}`}
                        onClick={() => setCabResultTab('deliberation')}
                      >
                        💬 Deliberation
                      </button>
                    )}
                    <button
                      className={`cab-tab-btn ${cabResultTab === 'decision' ? 'active' : ''}`}
                      onClick={() => setCabResultTab('decision')}
                    >
                      ⚖️ Decision
                    </button>
                    <button
                      className={`cab-tab-btn ${cabResultTab === 'flags' ? 'active' : ''}`}
                      onClick={() => setCabResultTab('flags')}
                    >
                      🚩 Required Changes
                      {flagCount > 0 && <span className="cab-tab-count">{flagCount}</span>}
                    </button>
                  </div>

                  <div className="cab-tab-panel">
                    {cabResultTab === 'deliberation' && cabSession && (
                      <div className="agent-logs">
                        {visibleAgentLogs.slice(0, visibleLogCount).map((log, idx) => {
                          const { meta, body, isSynthesis } = parseAgentLog(log);
                          return (
                            <div
                              key={idx}
                              className="agent-card log-reveal"
                              style={{ borderLeftColor: meta.color }}
                            >
                              <div className="agent-card-header">
                                <span className="agent-avatar" style={{ background: meta.color }}>
                                  {meta.icon}
                                </span>
                                <span className="agent-card-name" style={{ color: meta.color }}>
                                  {meta.label}
                                  {isSynthesis ? ' — Synthesis' : ''}
                                </span>
                              </div>
                              <div className="agent-card-body">
                                <ReactMarkdown>{body}</ReactMarkdown>
                              </div>
                            </div>
                          );
                        })}
                        {visibleLogCount < visibleAgentLogs.length && (
                          <div className="agent-log-entry log-typing">
                            <span className="typing-dot" />
                            <span className="typing-dot" />
                            <span className="typing-dot" />
                          </div>
                        )}
                      </div>
                    )}

                    {cabResultTab === 'decision' && (
                      <div className="decision-panel fade-in">
                        <DecisionBadge decision={decision} />
                        <div className="decision-reasoning">
                          <ReactMarkdown>{stripFlags(reasoning)}</ReactMarkdown>
                        </div>
                      </div>
                    )}

                    {cabResultTab === 'flags' && (
                      <div className="fade-in">
                        <FlagsPanel flags={flags} />
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      <footer className="app-footer">
        RFC Lifecycle Platform &middot; Every classification traces to the ITIL v6.1 Change
        Management process &middot; AI recommendations are advisory — humans retain final
        approval authority.
      </footer>
    </div>
  );
}

export default App;
