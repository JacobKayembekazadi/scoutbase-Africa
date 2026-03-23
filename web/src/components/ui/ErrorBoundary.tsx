"use client";

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { COLORS } from '@/lib/constants';

interface ErrorBoundaryProps {
    children: ReactNode;
    fallbackTitle?: string;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

/**
 * React Error Boundary (RL4-12)
 * Catches unhandled rendering errors in child components and displays
 * a friendly fallback UI instead of crashing the entire application.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('[ErrorBoundary] Caught error:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div
                    style={{
                        padding: 40,
                        textAlign: 'center',
                    }}
                    role="alert"
                >
                    <div
                        style={{
                            maxWidth: 500,
                            margin: '0 auto',
                            padding: 32,
                            background: COLORS.dangerDim,
                            borderRadius: 16,
                            border: `1px solid ${COLORS.danger}`,
                        }}
                    >
                        <div style={{ fontSize: 40, marginBottom: 16 }}>🚨</div>
                        <h2
                            style={{
                                fontSize: 18,
                                fontWeight: 700,
                                color: COLORS.danger,
                                marginBottom: 8,
                            }}
                        >
                            {this.props.fallbackTitle || 'Something went wrong'}
                        </h2>
                        <p
                            style={{
                                fontSize: 13,
                                color: COLORS.textDim,
                                marginBottom: 20,
                                lineHeight: 1.6,
                            }}
                        >
                            An unexpected error occurred in this section. The rest of the application
                            is unaffected.
                        </p>
                        {this.state.error && (
                            <details
                                style={{
                                    textAlign: 'left',
                                    marginBottom: 20,
                                    padding: 12,
                                    background: COLORS.surface,
                                    borderRadius: 8,
                                    fontSize: 11,
                                    color: COLORS.textMuted,
                                }}
                            >
                                <summary style={{ cursor: 'pointer', color: COLORS.textDim, fontWeight: 600 }}>
                                    Technical Details
                                </summary>
                                <pre
                                    style={{
                                        marginTop: 8,
                                        whiteSpace: 'pre-wrap',
                                        wordBreak: 'break-word',
                                        fontFamily: "'JetBrains Mono', monospace",
                                    }}
                                >
                                    {this.state.error.message}
                                </pre>
                            </details>
                        )}
                        <button
                            onClick={() => {
                                this.setState({ hasError: false, error: null });
                            }}
                            style={{
                                padding: '10px 24px',
                                borderRadius: 8,
                                border: 'none',
                                background: COLORS.accent,
                                color: COLORS.bg,
                                fontSize: 13,
                                fontWeight: 700,
                                cursor: 'pointer',
                            }}
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
