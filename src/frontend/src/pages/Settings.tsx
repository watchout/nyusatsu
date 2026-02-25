/**
 * Settings (P4) — company profile management page (SSOT-2 §6-8, SSOT-3 §4-8).
 *
 * Shows: company profile form with editable fields.
 * Saves via PATCH /company-profile.
 */

import { useCallback, useEffect, useState } from 'react';
import { fetchJson, patchJson } from '../services/api-client';
import type { CompanyProfile, CompanyProfileUpdate } from '../types/case';

export default function Settings() {
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form state
  const [form, setForm] = useState<CompanyProfileUpdate>({
    unified_qualification: false,
    grade: '',
    business_categories: [],
    regions: [],
  });

  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchJson<CompanyProfile>('/company-profile');
      setProfile(data);
      setForm({
        unified_qualification: data.unified_qualification,
        grade: data.grade,
        business_categories: data.business_categories,
        regions: data.regions,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleSave = async () => {
    setSaving(true);
    setSaveSuccess(false);
    try {
      await patchJson('/company-profile', form);
      setSaveSuccess(true);
      await loadProfile();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleArrayField = (field: 'business_categories' | 'regions', value: string) => {
    const items = value.split(',').map((s) => s.trim()).filter(Boolean);
    setForm((prev) => ({ ...prev, [field]: items }));
  };

  if (loading) {
    return (
      <div style={pageStyle}>
        <h1 style={titleStyle}>Settings</h1>
        <div data-testid="settings-loading">読み込み中…</div>
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div style={pageStyle}>
        <h1 style={titleStyle}>Settings</h1>
        <div data-testid="settings-error">エラー: {error}</div>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <h1 style={titleStyle}>Settings</h1>

      <div data-testid="company-profile-form" style={formContainerStyle}>
        <h2 style={sectionTitleStyle}>自社プロフィール</h2>

        {/* Unified qualification */}
        <div style={fieldStyle}>
          <label style={labelStyle}>
            <input
              type="checkbox"
              data-testid="field-unified-qualification"
              checked={form.unified_qualification ?? false}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, unified_qualification: e.target.checked }))
              }
              style={{ marginRight: 8 }}
            />
            全省庁統一資格
          </label>
        </div>

        {/* Grade */}
        <div style={fieldStyle}>
          <label style={labelStyle}>等級</label>
          <select
            data-testid="field-grade"
            value={form.grade ?? ''}
            onChange={(e) => setForm((prev) => ({ ...prev, grade: e.target.value }))}
            style={selectStyle}
          >
            <option value="">未設定</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
            <option value="D">D</option>
          </select>
        </div>

        {/* Business categories */}
        <div style={fieldStyle}>
          <label style={labelStyle}>営業品目（カンマ区切り）</label>
          <input
            type="text"
            data-testid="field-business-categories"
            value={(form.business_categories ?? []).join(', ')}
            onChange={(e) => handleArrayField('business_categories', e.target.value)}
            placeholder="物品の販売, 役務の提供"
            style={inputStyle}
          />
        </div>

        {/* Regions */}
        <div style={fieldStyle}>
          <label style={labelStyle}>競争参加地域（カンマ区切り）</label>
          <input
            type="text"
            data-testid="field-regions"
            value={(form.regions ?? []).join(', ')}
            onChange={(e) => handleArrayField('regions', e.target.value)}
            placeholder="関東, 近畿"
            style={inputStyle}
          />
        </div>

        {/* Save button */}
        <div style={buttonBarStyle}>
          <button
            data-testid="save-profile-btn"
            onClick={handleSave}
            disabled={saving}
            style={{
              ...saveButtonStyle,
              opacity: saving ? 0.5 : 1,
            }}
          >
            {saving ? '保存中…' : '保存'}
          </button>
          {saveSuccess && (
            <span data-testid="save-success" style={successStyle}>
              ✅ 保存しました
            </span>
          )}
          {error && profile && (
            <span data-testid="save-error" style={saveErrorStyle}>
              ⚠️ {error}
            </span>
          )}
        </div>

        {/* Last updated */}
        {profile && (
          <div style={metaStyle}>
            最終更新: {new Date(profile.updated_at).toLocaleString('ja-JP')}
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Styles ----

const pageStyle: React.CSSProperties = {
  padding: 16,
};

const titleStyle: React.CSSProperties = {
  fontSize: '1.25rem',
  fontWeight: 700,
  margin: '0 0 16px',
};

const formContainerStyle: React.CSSProperties = {
  maxWidth: 500,
  padding: 16,
  backgroundColor: '#f9fafb',
  border: '1px solid #e5e7eb',
  borderRadius: 8,
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: '1rem',
  fontWeight: 700,
  margin: '0 0 12px',
};

const fieldStyle: React.CSSProperties = {
  marginBottom: 12,
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.85rem',
  fontWeight: 600,
  color: '#374151',
  marginBottom: 4,
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  fontSize: '0.85rem',
  boxSizing: 'border-box',
};

const selectStyle: React.CSSProperties = {
  padding: '8px 10px',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  fontSize: '0.85rem',
  backgroundColor: '#fff',
};

const buttonBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 12,
  alignItems: 'center',
  marginTop: 16,
};

const saveButtonStyle: React.CSSProperties = {
  padding: '8px 24px',
  borderRadius: 6,
  border: 'none',
  backgroundColor: '#2563eb',
  color: '#fff',
  fontSize: '0.85rem',
  fontWeight: 600,
  cursor: 'pointer',
};

const successStyle: React.CSSProperties = {
  color: '#059669',
  fontSize: '0.85rem',
  fontWeight: 600,
};

const saveErrorStyle: React.CSSProperties = {
  color: '#dc2626',
  fontSize: '0.85rem',
};

const metaStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: '#9ca3af',
  marginTop: 12,
};
