'use client'

import { Toaster } from 'react-hot-toast'

/**
 * Toast provider — dodaj do root layout.
 * Używaj przez: import toast from 'react-hot-toast'; toast.success('...')
 */
export function ToastProvider() {
  return (
    <Toaster
      position="bottom-right"
      gutter={8}
      containerStyle={{ bottom: 24, right: 24 }}
      toastOptions={{
        duration: 3500,
        style: {
          background:   '#111827',
          color:        '#F8FAFC',
          border:       '1px solid rgba(255,255,255,0.08)',
          borderRadius: '10px',
          fontFamily:   'Inter, sans-serif',
          fontSize:     '13px',
          fontWeight:   500,
          padding:      '12px 16px',
          boxShadow:    '0 4px 20px rgba(0,0,0,0.4)',
        },
        success: {
          iconTheme: { primary: '#22C55E', secondary: '#111827' },
          style: { borderLeft: '3px solid #22C55E' },
        },
        error: {
          iconTheme: { primary: '#EF4444', secondary: '#111827' },
          style: { borderLeft: '3px solid #EF4444' },
          duration: 5000,
        },
        loading: {
          iconTheme: { primary: '#14B8A6', secondary: '#111827' },
          style: { borderLeft: '3px solid #14B8A6' },
        },
      }}
    />
  )
}
