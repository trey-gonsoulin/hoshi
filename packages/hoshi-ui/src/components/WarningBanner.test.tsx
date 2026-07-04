import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WarningBanner } from './WarningBanner'

describe('WarningBanner', () => {
  it('renders nothing when warnings is empty', () => {
    const { container } = render(<WarningBanner warnings={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders each warning message', () => {
    render(
      <WarningBanner
        warnings={['Time unknown — using noon UTC', 'Location unknown']}
      />,
    )
    expect(screen.getByText('Time unknown — using noon UTC')).toBeTruthy()
    expect(screen.getByText('Location unknown')).toBeTruthy()
  })

  it('renders a single warning', () => {
    render(<WarningBanner warnings={['One warning']} />)
    expect(screen.getByText('One warning')).toBeTruthy()
  })
})
