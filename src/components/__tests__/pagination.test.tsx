import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Pagination } from '../pagination'

describe('Pagination', () => {
  it('renders nothing when there is only one page', () => {
    const { container } = render(
      <Pagination page={1} count={10} pageSize={20} onChange={vi.fn()} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders page controls when count exceeds pageSize', () => {
    render(<Pagination page={1} count={50} pageSize={20} onChange={vi.fn()} />)
    expect(screen.getByText('1 / 3')).toBeInTheDocument()
    expect(screen.getByText('1–20 of 50')).toBeInTheDocument()
  })

  it('calls onChange with previous page when prev button clicked', () => {
    const onChange = vi.fn()
    render(<Pagination page={2} count={50} pageSize={20} onChange={onChange} />)
    fireEvent.click(screen.getByLabelText('Previous page'))
    expect(onChange).toHaveBeenCalledWith(1)
  })

  it('calls onChange with next page when next button clicked', () => {
    const onChange = vi.fn()
    render(<Pagination page={1} count={50} pageSize={20} onChange={onChange} />)
    fireEvent.click(screen.getByLabelText('Next page'))
    expect(onChange).toHaveBeenCalledWith(2)
  })

  it('disables prev button on first page', () => {
    render(<Pagination page={1} count={50} pageSize={20} onChange={vi.fn()} />)
    expect(screen.getByLabelText('Previous page')).toBeDisabled()
  })

  it('disables next button on last page', () => {
    render(<Pagination page={3} count={50} pageSize={20} onChange={vi.fn()} />)
    expect(screen.getByLabelText('Next page')).toBeDisabled()
  })

  it('displays correct range for middle page', () => {
    render(<Pagination page={2} count={50} pageSize={20} onChange={vi.fn()} />)
    expect(screen.getByText('21–40 of 50')).toBeInTheDocument()
  })

  it('clamps to range on last page with fewer items', () => {
    render(<Pagination page={3} count={45} pageSize={20} onChange={vi.fn()} />)
    expect(screen.getByText('41–45 of 45')).toBeInTheDocument()
  })
})
