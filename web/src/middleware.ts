import { NextResponse } from 'next/server'

// Firebase auth is handled client-side via AuthGuard.
// Middleware just passes through all requests.
export function middleware() {
    return NextResponse.next()
}

export const config = {
    matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
