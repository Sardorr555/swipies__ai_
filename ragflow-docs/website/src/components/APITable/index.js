import React from 'react';

export default function APITable({ children }) {
  return (
    <div style={{ overflowX: 'auto', margin: '1rem 0', width: '100%' }}>
      {children}
    </div>
  );
}
