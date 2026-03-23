import LoginForm from '@/components/auth/LoginForm'
import { COLORS } from '@/lib/constants'

export default function LoginPage() {
    return (
        <main className="flex h-screen w-full items-center justify-center p-4" style={{ background: COLORS.bg }}>
            <div className="relative mx-auto flex w-full max-w-[400px] flex-col space-y-2.5">
                <LoginForm />
            </div>
        </main>
    )
}
