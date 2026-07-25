import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './App.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('list');
  const [rfcs, setRfcs] = useState([]);
  const [selectedRfc, setSelectedRfc] = useState(null);
  const [cabSession, setCabSession] = useState(null);
  const [loading, setLoading] = useState(false);
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

  // Fetch RFC list on load
  useEffect(() => {
    fetchRfcList();
  }, []);

  const fetchRfcList = async () => {
    try {
      const response = await axios.get(`${API_BASE}/rfc-list`);
      setRfcs(response.data.rfcs);
    } catch (error) {
      console.error('Error fetching RFC list:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmitRfc = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        affected_systems: formData.affected_systems
          .split(',')
          .map((s) => s.trim()),
        estimated_downtime_hours: parseFloat(
          formData.estimated_downtime_hours
        ),
      };

      const response = await axios.post(`${API_BASE}/rfc/submit`, payload);
      alert(`✅ RFC submitted: ${response.data.rfc_number}`);
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
      alert(`❌ Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleViewRfc = async (rfc_id) => {
    try {
      const response = await axios.get(`${API_BASE}/rfc/${rfc_id}`);
      setSelectedRfc(response.data);
      setCabSession(null);
    } catch (error) {
      console.error('Error fetching RFC:', error);
    }
  };

  const handleTriggerCab = async (rfc_id) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/rfc/${rfc_id}/trigger-cab`);
      setCabSession(response.data);
    } catch (error) {
      alert(`❌ CAB session failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🚀 RFC Lifecycle PoC</h1>
        <p>AI-Powered Change Management with Virtual CAB Deliberation</p>
      </header>

      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          📋 RFC List
        </button>
        <button
          className={`tab-btn ${activeTab === 'submit' ? 'active' : ''}`}
          onClick={() => setActiveTab('submit')}
        >
          ➕ Submit RFC
        </button>
      </div>

      {activeTab === 'list' && (
        <div className="content">
          <div className="rfc-list">
            <h2>All RFCs</h2>
            {rfcs.length === 0 ? (
              <p>No RFCs yet. Create one!</p>
            ) : (
              <div className="rfc-cards">
                {rfcs.map((rfc) => (
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
                      <span className={`badge type-${rfc.change_type}`}>
                        {rfc.change_type}
                      </span>
                      <span className={`badge status-${rfc.status}`}>
                        {rfc.status}
                      </span>
                    </div>
                    <p className="rfc-date">
                      {new Date(rfc.created_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'submit' && (
        <div className="content">
          <div className="submit-form">
            <h2>Submit New RFC</h2>
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

              <button
                type="submit"
                className="btn-primary"
                disabled={loading}
              >
                {loading ? 'Submitting...' : '✅ Submit RFC'}
              </button>
            </form>
          </div>
        </div>
      )}

      {activeTab === 'detail' && selectedRfc && (
        <div className="content">
          <div className="rfc-detail">
            <button
              className="btn-back"
              onClick={() => setActiveTab('list')}
            >
              ← Back to List
            </button>

            <h2>{selectedRfc.title}</h2>
            <div className="detail-meta">
              <div className="meta-item">
                <strong>RFC Number:</strong> {selectedRfc.rfc_number}
              </div>
              <div className="meta-item">
                <strong>Type:</strong>{' '}
                <span className={`badge type-${selectedRfc.change_type}`}>
                  {selectedRfc.change_type}
                </span>
              </div>
              <div className="meta-item">
                <strong>Status:</strong>{' '}
                <span className={`badge status-${selectedRfc.status}`}>
                  {selectedRfc.status}
                </span>
              </div>
              <div className="meta-item">
                <strong>Impact:</strong> {selectedRfc.impact}
              </div>
              <div className="meta-item">
                <strong>Priority:</strong> {selectedRfc.priority}
              </div>
              {selectedRfc.risk_level && (
                <div className="meta-item">
                  <strong>Risk Level:</strong> {selectedRfc.risk_level}/5
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
                <h3>Test Cases & Results</h3>
                <p>{selectedRfc.test_cases}</p>
              </div>
            )}

            {selectedRfc.back_out_plan && (
              <div className="detail-section">
                <h3>Rollback/Back-Out Plan</h3>
                <p>{selectedRfc.back_out_plan}</p>
              </div>
            )}

            {selectedRfc.auto_approved && (
              <div className="detail-section alert alert-success">
                ✅ <strong>Auto-Approved:</strong> This RFC matches a Standard
                Change Catalogue entry and was auto-approved.
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
                  {loading
                    ? '⏳ Running CAB Session...'
                    : '🎯 Trigger AI CAB Review'}
                </button>
              )}

            {cabSession && (
              <div className="cab-session">
                <h3>🏛️ AI CAB Deliberation Session</h3>
                <div className="agent-logs">
                  {cabSession.agent_logs.map((log, idx) => (
                    <div key={idx} className="agent-log-entry">
                      <ReactMarkdown>{log}</ReactMarkdown>
                    </div>
                  ))}
                </div>

                <div className="cab-decision-box">
                  <h4>🎯 Final Decision: {cabSession.cab_decision}</h4>
                  <div className="decision-reasoning">
                    <ReactMarkdown>{cabSession.cab_reasoning}</ReactMarkdown>
                  </div>
                </div>
              </div>
            )}

            {selectedRfc.cab_decision && (
              <div className="cab-session">
                <h3>🏛️ CAB Decision (Cached)</h3>
                <div className="cab-decision-box">
                  <h4>🎯 Final Decision: {selectedRfc.cab_decision}</h4>
                  <div className="decision-reasoning">
                    <ReactMarkdown>{selectedRfc.cab_reasoning}</ReactMarkdown>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
