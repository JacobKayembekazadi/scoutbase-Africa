'use client'

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { onAuthChange, auth, getRedirectResult } from '@/lib/firebase'
import type { User } from 'firebase/auth'

interface AuthContextType {
    user: User | null
    loading: boolean
}

const AuthContext = createContext<AuthContextType>({ user: null, loading: true })

export function useAuth() {
    return useContext(AuthContext)
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Handle redirect result after Google sign-in returns
        getRedirectResult(auth).catch(() => {
            // Redirect result errors are non-fatal (e.g., no redirect pending)
        })

        const unsubscribe = onAuthChange((firebaseUser) => {
            setUser(firebaseUser)
            setLoading(false)
        })
        return unsubscribe
    }, [])

    return (
        <AuthContext.Provider value={{ user, loading }}>
            {children}
        </AuthContext.Provider>
    )
}
