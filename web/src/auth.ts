import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"
import { authConfig } from "./auth.config"

export const { handlers, auth, signIn, signOut } = NextAuth({
    ...authConfig,
    providers: [
        Credentials({
            credentials: {
                email: { type: "email" },
                password: { type: "password" }
            },
            async authorize(credentials) {
                // Add custom login logic here
                // This is where you would lookup user from database
                // For now, we hardcode or use environment variables

                const adminEmail = process.env.ADMIN_EMAIL || "admin@scoutbase.com"
                const adminPass = process.env.ADMIN_PASSWORD || "scoutbase2026"

                if (credentials.email === adminEmail && credentials.password === adminPass) {
                    return {
                        id: "1",
                        email: adminEmail,
                        name: "Admin User",
                    }
                }
                return null
            }
        })
    ],
})
