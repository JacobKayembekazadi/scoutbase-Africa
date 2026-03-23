import { initializeApp, getApps } from 'firebase/app'
import {
    getAuth,
    GoogleAuthProvider,
    signInWithRedirect,
    getRedirectResult,
    signOut as firebaseSignOut,
    onAuthStateChanged,
    type User,
} from 'firebase/auth'

const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
}

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0]
export const auth = getAuth(app)

const googleProvider = new GoogleAuthProvider()

export async function signInWithGoogle() {
    // Use redirect instead of popup to avoid COOP issues on Vercel
    await signInWithRedirect(auth, googleProvider)
}

export { getRedirectResult }

export async function signOut() {
    await firebaseSignOut(auth)
}

export function onAuthChange(callback: (user: User | null) => void) {
    return onAuthStateChanged(auth, callback)
}

export async function getFirebaseToken(): Promise<string | null> {
    const user = auth.currentUser
    if (!user) return null
    return user.getIdToken()
}
