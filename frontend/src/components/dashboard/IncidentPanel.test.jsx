import React from 'react';
import { render, screen } from '@testing-library/react';
import IncidentPanel from './IncidentPanel';
import { INCIDENT_SEVERITY } from '../../utils/constants';

describe('IncidentPanel Accessibility and State Updates', () => {
  it('renders without crashing and updates aria-live region correctly', () => {
    const incidents = [
      {
        incident_id: '123',
        severity: INCIDENT_SEVERITY.CRITICAL,
        incident_type: 'medical_emergency',
        description: 'Passenger ill in section 120',
        location: 'Section 120',
        timestamp: Date.now(),
      }
    ];

    render(<IncidentPanel incidents={incidents} />);

    // Verify aria-live region exists
    const alertRegion = screen.getByRole('alert');
    expect(alertRegion).toHaveAttribute('aria-live', 'assertive');
    
    // Verify the incident is rendered
    expect(screen.getByText(/Passenger ill in section 120/i)).toBeInTheDocument();
  });
});
