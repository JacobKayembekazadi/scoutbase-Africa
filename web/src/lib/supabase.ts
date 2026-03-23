/**
 * Supabase Client Configuration
 * ==============================
 * Browser-side Supabase client for auth and storage.
 */

import { createBrowserClient } from '@supabase/ssr'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export function createClient() {
    return createBrowserClient(supabaseUrl, supabaseAnonKey)
}

/**
 * Get the current session's JWT token for API calls.
 * Returns null if not authenticated.
 */
export async function getAccessToken(): Promise<string | null> {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ?? null
}
