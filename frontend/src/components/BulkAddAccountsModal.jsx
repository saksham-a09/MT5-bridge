import React, { useState, useMemo, useRef } from 'react';
import { 
  X, Upload, CheckCircle2, AlertTriangle, AlertCircle, 
  Trash2, RefreshCw, Server, ArrowRight
} from 'lucide-react';
import { createAccountsBulk } from '../services/api';

/**
 * Simple parser for CSV, TSV, colon-separated, or JSON MT5 account lists.
 */
function parseAccounts(rawText, defaultServer = '', defaultNode = 'auto') {
  if (!rawText || !rawText.trim()) return [];

  const text = rawText.replace(/^\uFEFF/, '').trim();

  // Try JSON
  if (text.startsWith('[') && text.endsWith(']')) {
    try {
      const arr = JSON.parse(text);
      if (Array.isArray(arr)) {
        return arr.map((item, idx) => ({
          id: `row-${idx}`,
          login: item.login ? String(item.login).trim() : '',
          password: item.password ? String(item.password).trim() : '',
          server: item.server ? String(item.server).trim() : defaultServer,
          name: item.name ? String(item.name).trim() : '',
          target_node_id: item.target_node_id || item.node || defaultNode || 'auto'
        }));
      }
    } catch {
      // fallback
    }
  }

  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l && !l.startsWith('#'));
  if (!lines.length) return [];

  // Delimiter sniffing
  const first = lines[0];
  let delimiter = ',';
  if (first.includes('\t')) delimiter = '\t';
  else if (first.includes(';') && !first.includes(',')) delimiter = ';';
  else if (first.includes('|')) delimiter = '|';
  else if (first.includes(':') && !first.includes(',')) delimiter = ':';

  // Check header
  const firstLower = first.toLowerCase();
  const hasHeader = ['login', 'account', 'server', 'password', 'broker'].some(k => firstLower.includes(k));

  let headers = null;
  let dataLines = lines;

  if (hasHeader) {
    headers = lines[0].split(delimiter).map(h => h.trim().toLowerCase().replace(/[\s-_]+/g, ''));
    dataLines = lines.slice(1);
  }

  const accounts = [];

  dataLines.forEach((line, idx) => {
    if (!line) return;
    const parts = line.split(delimiter).map(p => p.trim());
    if (!parts.length || !parts[0]) return;

    let login = '';
    let password = '';
    let server = defaultServer;
    let name = '';
    let target_node_id = defaultNode;

    if (headers) {
      headers.forEach((h, colIdx) => {
        const val = parts[colIdx] || '';
        if (['login', 'account', 'accountid', 'accountnumber', 'id'].includes(h)) {
          login = val;
        } else if (['password', 'pass', 'pwd'].includes(h)) {
          password = val;
        } else if (['server', 'broker', 'brokerserver'].includes(h)) {
          server = val || defaultServer;
        } else if (['name', 'label', 'accountname', 'user'].includes(h)) {
          name = val;
        } else if (['node', 'targetnodeid', 'targetnode', 'nodeid'].includes(h)) {
          target_node_id = val || defaultNode;
        }
      });
    } else {
      // Headerless: login, password, server, name, node
      login = parts[0] || '';
      password = parts[1] || '';
      server = parts[2] || defaultServer;
      name = parts[3] || '';
      target_node_id = parts[4] || defaultNode;
    }

    accounts.push({
      id: `row-${idx}`,
      login,
      password,
      server,
      name: name || (login ? `Account ${login}` : ''),
      target_node_id: target_node_id || 'auto'
    });
  });

  return accounts;
}

export default function BulkAddAccountsModal({ nodes = [], onClose, onSuccess }) {
  const [rawText, setRawText] = useState('');
  const [defaultServer, setDefaultServer] = useState('VantageMarkets-Demo');
  const [defaultNode, setDefaultNode] = useState('auto');
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [resultMsg, setResultMsg] = useState(null);

  const fileInputRef = useRef(null);

  // Parse accounts
  const parsed = useMemo(() => {
    return parseAccounts(rawText, defaultServer, defaultNode);
  }, [rawText, defaultServer, defaultNode]);

  // Validation
  const validated = useMemo(() => {
    const loginCount = {};
    parsed.forEach(a => {
      const l = String(a.login || '').trim();
      if (l) loginCount[l] = (loginCount[l] || 0) + 1;
    });

    return parsed.map(a => {
      const errs = [];
      const cleanLogin = String(a.login || '').trim();
      const loginNum = parseInt(cleanLogin, 10);

      if (!cleanLogin) errs.push('Missing Login');
      else if (isNaN(loginNum) || loginNum <= 0 || !/^\d+$/.test(cleanLogin)) errs.push('Login must be digits');
      else if (loginCount[cleanLogin] > 1) errs.push('Duplicate Login');

      if (!a.password) errs.push('Missing Password');
      if (!a.server) errs.push('Missing Server');

      return {
        ...a,
        loginNum: isNaN(loginNum) ? null : loginNum,
        isValid: errs.length === 0,
        error: errs.join(', ')
      };
    });
  }, [parsed]);

  const validAccounts = validated.filter(a => a.isValid);
  const validCount = validAccounts.length;

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setRawText(event.target.result || '');
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleDeleteRow = (rowId) => {
    const remaining = parsed.filter(a => a.id !== rowId);
    if (!remaining.length) {
      setRawText('');
      return;
    }
    const newText = remaining.map(a => `${a.login},${a.password},${a.server}`).join('\n');
    setRawText(newText);
  };

  const handleSubmit = async () => {
    setSubmitError('');
    if (!validCount) {
      setSubmitError('Please enter at least one valid account with Login, Password, and Server.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        overwrite_existing: true,
        accounts: validAccounts.map(a => ({
          login: a.loginNum,
          password: a.password,
          server: a.server,
          name: a.name || `Account ${a.loginNum}`,
          target_node_id: a.target_node_id || 'auto'
        }))
      };

      const res = await createAccountsBulk(payload);
      if (!res.success) throw new Error(res.message || 'Failed to add accounts');

      setResultMsg(`Successfully added ${res.created} new and updated ${res.updated} accounts!`);
      if (onSuccess) onSuccess(res);
    } catch (err) {
      setSubmitError(err.message || 'Failed to import accounts');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '680px' }}
      >
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0 }}>
              Add Accounts in Bulk
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '2px 0 0' }}>
              Paste accounts or upload a CSV file to add multiple MT5 terminals at once
            </p>
          </div>
          <button onClick={onClose} className="btn btn-secondary btn-icon" style={{ borderRadius: '50%' }}>
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Result Alert */}
          {resultMsg && (
            <div style={{
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} />
                <span>{resultMsg}</span>
              </div>
              <button 
                className="btn btn-primary btn-sm"
                onClick={onClose}
                style={{ padding: '4px 12px', fontSize: '0.78rem' }}
              >
                Done
              </button>
            </div>
          )}

          {/* Error Alert */}
          {submitError && (
            <div style={{
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(244, 63, 94, 0.15)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              color: '#fb7185',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <AlertCircle size={15} />
              <span>{submitError}</span>
            </div>
          )}

          {/* Textarea Label & Quick Actions */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--text-muted)' }}>
                Accounts List (one per line)
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.txt,.tsv"
                  style={{ display: 'none' }}
                  onChange={handleFileUpload}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.74rem', padding: '4px 10px', height: '26px' }}
                >
                  <Upload size={12} />
                  <span>Upload CSV</span>
                </button>
              </div>
            </div>

            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder={`Paste your MT5 credentials here. Example formats:\n\n25506235, MyPassword123, VantageMarkets-Demo\n25506236:MyPassword456:VantageMarkets-Demo\n25506237, MyPassword789`}
              rows={5}
              className="input-field font-mono"
              style={{
                fontSize: '0.82rem',
                lineHeight: '1.45',
                padding: '10px 12px',
                resize: 'vertical',
                minHeight: '110px'
              }}
            />
          </div>

          {/* Defaults (Server & Node) */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '600' }}>
                Broker Server (if omitted above)
              </label>
              <input
                type="text"
                placeholder="e.g. VantageMarkets-Demo"
                value={defaultServer}
                onChange={(e) => setDefaultServer(e.target.value)}
                className="input-field"
                style={{ fontSize: '0.82rem' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '600' }}>
                Assigned Node
              </label>
              <select
                value={defaultNode}
                onChange={(e) => setDefaultNode(e.target.value)}
                className="input-field"
                style={{ fontSize: '0.82rem' }}
              >
                <option value="auto">Auto-Balance (Recommended)</option>
                {nodes.map(n => (
                  <option key={n.node_id} value={n.node_id}>
                    {n.name} ({n.node_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Preview Table */}
          {validated.length > 0 && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
                  Detected Accounts ({validated.length})
                </span>
                <span style={{ fontSize: '0.74rem', color: validCount > 0 ? '#34d399' : '#fb7185' }}>
                  {validCount} ready to add
                </span>
              </div>

              <div style={{
                maxHeight: '180px',
                overflowY: 'auto',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                background: 'rgba(0, 0, 0, 0.25)'
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'rgba(15, 23, 42, 0.9)', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)' }}>
                      <th style={{ padding: '6px 10px' }}>Login</th>
                      <th style={{ padding: '6px 10px' }}>Password</th>
                      <th style={{ padding: '6px 10px' }}>Server</th>
                      <th style={{ padding: '6px 10px' }}>Status</th>
                      <th style={{ padding: '6px 10px', textAlign: 'right', width: '30px' }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {validated.map((acc) => (
                      <tr 
                        key={acc.id}
                        style={{
                          borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                          background: !acc.isValid ? 'rgba(244, 63, 94, 0.08)' : 'transparent'
                        }}
                      >
                        <td style={{ padding: '6px 10px' }} className="font-mono">
                          <span style={{ fontWeight: '600', color: acc.login ? '#ffffff' : '#fb7185' }}>
                            {acc.login || '<Missing>'}
                          </span>
                        </td>
                        <td style={{ padding: '6px 10px', color: 'var(--text-secondary)' }} className="font-mono">
                          ••••••••
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <span style={{ color: acc.server ? 'var(--text-main)' : '#fb7185' }}>
                            {acc.server || '<Missing>'}
                          </span>
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          {acc.isValid ? (
                            <span style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '3px' }}>
                              <CheckCircle2 size={12} /> Ready
                            </span>
                          ) : (
                            <span style={{ color: '#fb7185', display: 'flex', alignItems: 'center', gap: '3px' }}>
                              <AlertTriangle size={12} /> {acc.error}
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '6px 10px', textAlign: 'right' }}>
                          <button
                            type="button"
                            onClick={() => handleDeleteRow(acc.id)}
                            style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
                            onMouseEnter={(e) => e.currentTarget.style.color = '#fb7185'}
                            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-dim)'}
                          >
                            <Trash2 size={12} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {validCount > 0 ? `${validCount} valid accounts ready` : 'No valid accounts'}
          </span>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              id="btn-submit-bulk-simple"
              type="button"
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={loading || !validCount}
            >
              {loading ? (
                <>
                  <RefreshCw size={14} className="spin" />
                  <span>Adding...</span>
                </>
              ) : (
                <span>Add {validCount > 0 ? `${validCount} Accounts` : 'Accounts'}</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
