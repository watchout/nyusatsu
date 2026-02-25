import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from '../src/App.tsx'

// Mock fetch for components that fetch on mount
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()
  mockFetch.mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ data: null, meta: { page: 1, limit: 20, total: 0, total_pages: 0 } }),
    }),
  )
})

function renderWithRouter(initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <App />
    </MemoryRouter>,
  )
}

describe('App routing', () => {
  it('renders Dashboard at /', async () => {
    renderWithRouter('/')
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument()
  })

  it('renders CaseDetail at /cases/:id', async () => {
    renderWithRouter('/cases/abc-123')
    // CaseDetail now shows loading state first, then case name
    await waitFor(() => {
      expect(screen.getByText('読み込み中…')).toBeInTheDocument()
    })
  })

  it('renders Analytics at /analytics', () => {
    renderWithRouter('/analytics')
    expect(screen.getByRole('heading', { name: /analytics/i })).toBeInTheDocument()
  })

  it('renders Settings at /settings', () => {
    renderWithRouter('/settings')
    expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument()
  })
})
