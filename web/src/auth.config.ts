import type { NextAuthConfig } from "next-auth"

export const authConfig = {
    pages: {
        signIn: '/login',
    },
    callbacks: {
        authorized({ auth, request: { nextUrl } }) {
            const isLoggedIn = !!auth?.user
            const isOnLogin = nextUrl.pathname.startsWith('/login')

            // If on login page and logged in, redirect to dashboard
            if (isOnLogin) {
                if (isLoggedIn) return Response.redirect(new URL('/', nextUrl))
                return true
            }

            // If logged in, allow access
            if (isLoggedIn) return true

            // Redirect unauthenticated users to login page
            return false
        },
    },
    providers: [],
} satisfies NextAuthConfig
