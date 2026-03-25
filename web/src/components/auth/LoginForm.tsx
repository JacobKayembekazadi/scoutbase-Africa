'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase'
import { useAuth } from '@/components/auth/AuthProvider'
import { COLORS } from '@/lib/constants'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function LoginForm() {
    const [loading, setLoading] = useState(false)
    const { user } = useAuth()
    const router = useRouter()

    // If user is already signed in (e.g., returning from OAuth redirect), go to dashboard
    useEffect(() => {
        if (user) router.push('/')
    }, [user, router])

    async function handleGoogleSignIn() {
        setLoading(true)
        const supabase = createClient()
        const { error } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: typeof window !== 'undefined' ? window.location.origin : undefined,
            },
        })
        if (error) {
            console.error('Login error:', error)
            setLoading(false)
        }
        // On success, Supabase redirects the browser — no further action needed
    }

    return (
        <div className="space-y-3">
            <div
                className="flex-1 rounded-lg px-6 pb-6 pt-8"
                style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
            >
                <h1 className="mb-3 text-2xl font-bold" style={{ color: COLORS.text }}>
                    ScoutBase Africa
                </h1>
                <p className="mb-6 text-sm" style={{ color: COLORS.textDim }}>
                    Sign in to access the scouting dashboard.
                </p>

                <button
                    onClick={handleGoogleSignIn}
                    disabled={loading}
                    className="flex w-full items-center justify-center gap-3 rounded-lg px-4 py-3 text-sm font-semibold transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
                    style={{
                        background: '#fff',
                        color: '#1f2937',
                        border: `1px solid ${COLORS.border}`,
                    }}
                >
                    <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                        <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4" />
                        <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853" />
                        <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.997 8.997 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05" />
                        <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335" />
                    </svg>
                    {loading ? 'Redirecting to Google...' : 'Continue with Google'}
                </button>

                <p className="mt-6 text-center text-xs" style={{ color: COLORS.textMuted }}>
                    Only authorized scouts and staff can access this platform.
                </p>
            </div>
        </div>
    )
}
