/**
 * Tests for Settings page — TASK-46.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const baseProfile = {
  id: 'prof-1',
  unified_qualification: true,
  grade: 'D',
  business_categories: ['物品の販売', '役務の提供'],
  regions: ['関東', '近畿'],
  licenses: [],
  certifications: [],
  experience: [],
  subcontractors: [],
  updated_at: '2026-02-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
};

function setupMock(profileData: Record<string, unknown> | null = baseProfile) {
  mockFetch.mockImplementation((...args: unknown[]) => {
    const url = String(args[0] ?? '');
    if (url.includes('/api/v1/company-profile')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: profileData }),
      });
    }
    if (url.includes('/api/v1/batch/latest')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null }),
      });
    }
    if (url.includes('/api/v1/cases')) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [],
            meta: { page: 1, limit: 20, total: 0, total_pages: 0 },
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ data: null }),
    });
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

function renderSettings() {
  return render(
    <MemoryRouter initialEntries={['/settings']}>
      <App />
    </MemoryRouter>,
  );
}

describe('Settings', () => {
  it('renders Settings heading', async () => {
    setupMock();
    renderSettings();
    expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument();
  });

  it('shows company profile form', async () => {
    setupMock();
    renderSettings();
    await waitFor(() => {
      expect(screen.getByTestId('company-profile-form')).toBeInTheDocument();
    });
  });

  it('loads unified qualification checkbox', async () => {
    setupMock();
    renderSettings();
    await waitFor(() => {
      expect(screen.getByTestId('field-unified-qualification')).toBeInTheDocument();
    });
    const checkbox = screen.getByTestId('field-unified-qualification') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('loads grade select', async () => {
    setupMock();
    renderSettings();
    await waitFor(() => {
      expect(screen.getByTestId('field-grade')).toBeInTheDocument();
    });
    const select = screen.getByTestId('field-grade') as HTMLSelectElement;
    expect(select.value).toBe('D');
  });

  it('loads business categories', async () => {
    setupMock();
    renderSettings();
    await waitFor(() => {
      expect(screen.getByTestId('field-business-categories')).toBeInTheDocument();
    });
    const input = screen.getByTestId('field-business-categories') as HTMLInputElement;
    expect(input.value).toContain('物品の販売');
    expect(input.value).toContain('役務の提供');
  });

  it('loads regions', async () => {
    setupMock();
    renderSettings();
    await waitFor(() => {
      expect(screen.getByTestId('field-regions')).toBeInTheDocument();
    });
    const input = screen.getByTestId('field-regions') as HTMLInputElement;
    expect(input.value).toContain('関東');
    expect(input.value).toContain('近畿');
  });

  it('shows save button', async () => {
    setupMock();
    renderSettings();
    await waitFor(() => {
      expect(screen.getByTestId('save-profile-btn')).toBeInTheDocument();
    });
    expect(screen.getByTestId('save-profile-btn')).toHaveTextContent('保存');
  });
});
