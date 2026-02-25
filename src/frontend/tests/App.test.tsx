import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import App from '../src/App.tsx'

function renderWithRouter(initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <App />
    </MemoryRouter>,
  )
}

describe('App routing', () => {
  it('renders Dashboard at /', () => {
    renderWithRouter('/')
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument()
  })

  it('renders CaseDetail at /cases/:id', () => {
    renderWithRouter('/cases/abc-123')
    expect(screen.getByRole('heading', { name: /case detail/i })).toBeInTheDocument()
    expect(screen.getByText(/abc-123/)).toBeInTheDocument()
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
