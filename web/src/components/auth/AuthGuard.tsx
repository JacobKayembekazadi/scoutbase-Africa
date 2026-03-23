'use client'

import { useAuth } from './AuthProvider'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { COLORS } from '@/lib/constants'

export function AuthGuard({ children }: { children: React.ReactNode }) {
    const { user, loading } = useAuth()
    const router = useRouter()

    useEffect(() => {
        if (!loading && !user) {
            router.push('/login')
        }
    }, [user, loading, router])

    if (loading) {
        return (
            <div className="flex h-screen w-full items-center justify-center" style={{ background: COLORS.bg }}>
                <div className="text-sm" style={{ color: COLORS.textDim }}>Loading...</div>
            </div>
        )
    }

    if (!user) return null

    return <>{children}</>
}
