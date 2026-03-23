'use client'

import { useActionState } from 'react'
import { authenticate } from '@/lib/actions'
import { COLORS } from '@/lib/constants'

export default function LoginForm() {
    const [errorMessage, formAction, isPending] = useActionState(authenticate, undefined)

    return (
        <form action={formAction} className="space-y-3">
            <div className="flex-1 rounded-lg px-6 pb-4 pt-8" style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}>
                <h1 className="mb-3 text-2xl font-bold" style={{ color: COLORS.text }}>
                    ScoutBase Africa
                </h1>
                <p className="mb-6 text-sm" style={{ color: COLORS.textDim }}>
                    Please log in to verify your identity.
                </p>

                <div className="w-full">
                    <div>
                        <label className="mb-3 mt-5 block text-xs font-medium uppercase tracking-wider" htmlFor="email" style={{ color: COLORS.textDim }}>
                            Email
                        </label>
                        <div className="relative">
                            <input
                                className="peer block w-full rounded-md py-[9px] pl-3 text-sm outline-none focus:ring-1"
                                id="email"
                                type="email"
                                name="email"
                                placeholder="Enter your email address"
                                required
                                style={{
                                    background: COLORS.bg,
                                    borderColor: COLORS.border,
                                    color: COLORS.text,
                                    border: `1px solid ${COLORS.border}`
                                }}
                            />
                        </div>
                    </div>
                    <div className="mt-4">
                        <label className="mb-3 mt-5 block text-xs font-medium uppercase tracking-wider" htmlFor="password" style={{ color: COLORS.textDim }}>
                            Password
                        </label>
                        <div className="relative">
                            <input
                                className="peer block w-full rounded-md py-[9px] pl-3 text-sm outline-none focus:ring-1"
                                id="password"
                                type="password"
                                name="password"
                                placeholder="Enter password"
                                required
                                minLength={6}
                                style={{
                                    background: COLORS.bg,
                                    borderColor: COLORS.border,
                                    color: COLORS.text,
                                    border: `1px solid ${COLORS.border}`
                                }}
                            />
                        </div>
                    </div>
                </div>
                <button
                    className="mt-6 w-full rounded-lg px-4 py-2 text-sm font-bold uppercase tracking-wider transition-all hover:brightness-110 active:scale-[0.98]"
                    disabled={isPending}
                    style={{ background: COLORS.accent, color: COLORS.bg }}
                >
                    {isPending ? "Verifying..." : "Log in"}
                </button>
                <div
                    className="flex h-8 items-end space-x-1"
                    aria-live="polite"
                    aria-atomic="true"
                >
                    {errorMessage && (
                        <p className="text-sm font-medium" style={{ color: COLORS.danger }}>
                            {errorMessage}
                        </p>
                    )}
                </div>
            </div>
        </form>
    )
}
