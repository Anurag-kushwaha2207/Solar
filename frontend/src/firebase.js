/**
 * Firebase Client Configuration & Service Layer for UrjaMind
 * ============================================================
 * Handles:
 * 1. Authentication (Google Sign-In, Email/Password, Factory Supervisor Phone Auth)
 * 2. Cloud Storage (Electricity Bill PDFs, Meter interval data files)
 * 3. Cloud Firestore (Plant Profiles, Copilot Chat Transcripts, Historical Energy Records)
 */
import { initializeApp, getApps, getApp } from 'firebase/app'
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
} from 'firebase/auth'
import {
  getFirestore,
  doc,
  setDoc,
  getDoc,
  collection,
  addDoc,
  serverTimestamp,
} from 'firebase/firestore'
import {
  getStorage,
  ref,
  uploadBytes,
  getDownloadURL,
} from 'firebase/storage'

// Read credentials from environment variables
const apiKey = import.meta.env.VITE_FIREBASE_API_KEY || ''
const authDomain = import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || ''
const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID || ''
const storageBucket = import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || ''
const messagingSenderId = import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || ''
const appId = import.meta.env.VITE_FIREBASE_APP_ID || ''

// Honest configuration flag: True ONLY if real credentials are provided
export const isFirebaseConfigured = Boolean(
  apiKey &&
  projectId &&
  projectId !== 'unconfigured' &&
  !apiKey.includes('Placeholder') &&
  !apiKey.includes('DemoKey')
)

const firebaseConfig = {
  apiKey: apiKey || 'AIzaSy_UNCONFIGURED_KEY',
  authDomain: authDomain || 'urjamind-energy.firebaseapp.com',
  projectId: projectId || 'urjamind-energy',
  storageBucket: storageBucket || 'urjamind-energy.firebasestorage.app',
  messagingSenderId: messagingSenderId || '724779527706',
  appId: appId || '1:724779527706:web:c11a02d6bc088feb6a6ba3',
}

// Initialize Firebase safely
export const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp()
export const auth = getAuth(app)
export const db = getFirestore(app)
export const storage = getStorage(app)
export const googleProvider = new GoogleAuthProvider()

/**
 * Returns current authenticated user UID as plantId, or 'plant_demo' as guest fallback.
 */
export const getCurrentPlantId = () => {
  return auth?.currentUser?.uid || 'plant_demo'
}

// ── Auth Helpers ─────────────────────────────────────────────────────────────
export const loginWithGoogle = async () => {
  if (!isFirebaseConfigured) {
    return {
      success: false,
      error: 'Firebase is not configured. Please add your VITE_FIREBASE_* credentials in frontend/.env to enable Google Authentication.',
    }
  }
  try {
    const result = await signInWithPopup(auth, googleProvider)
    return { success: true, user: result.user }
  } catch (err) {
    console.warn("Firebase Google login error:", err)
    return { success: false, error: err.message }
  }
}

export const loginWithEmail = async (email, password) => {
  if (!isFirebaseConfigured) {
    return {
      success: false,
      error: 'Firebase is not configured. Please add your VITE_FIREBASE_* credentials in frontend/.env to enable Email Authentication.',
    }
  }
  try {
    const cred = await signInWithEmailAndPassword(auth, email, password)
    return { success: true, user: cred.user }
  } catch (err) {
    console.warn("Firebase email login error:", err)
    return { success: false, error: err.message }
  }
}

export const signupWithEmail = async (email, password) => {
  try {
    const cred = await createUserWithEmailAndPassword(auth, email, password)
    return { success: true, user: cred.user }
  } catch (err) {
    console.warn("Firebase signup error:", err)
    return { success: false, error: err.message }
  }
}

export const logoutUser = async () => {
  try {
    await signOut(auth)
    return { success: true }
  } catch (err) {
    return { success: false, error: err.message }
  }
}

export const subscribeAuth = (callback) => {
  return onAuthStateChanged(auth, callback)
}

// ── Storage Helpers ──────────────────────────────────────────────────────────
export const uploadBillDocument = async (file, plantId = null) => {
  const targetPlantId = plantId || getCurrentPlantId()
  if (!isFirebaseConfigured) {
    return { success: false, error: 'Firebase Storage not configured' }
  }
  try {
    const timestamp = Date.now()
    const storageRef = ref(storage, `bills/${targetPlantId}/${timestamp}_${file.name}`)
    const snapshot = await uploadBytes(storageRef, file)
    const downloadUrl = await getDownloadURL(snapshot.ref)
    return { success: true, downloadUrl, path: snapshot.ref.fullPath }
  } catch (err) {
    console.warn("Firebase storage upload error (using local API fallback):", err)
    return { success: false, error: err.message }
  }
}

// ── Firestore Helpers ────────────────────────────────────────────────────────
export const savePlantRecord = async (plantId = null, data) => {
  const targetPlantId = plantId || getCurrentPlantId()
  if (!isFirebaseConfigured) {
    return { success: false, error: 'Firestore not configured' }
  }
  try {
    const plantRef = doc(db, "plants", String(targetPlantId))
    await setDoc(plantRef, { ...data, updatedAt: serverTimestamp() }, { merge: true })
    return { success: true }
  } catch (err) {
    console.warn("Firestore save error:", err)
    return { success: false, error: err.message }
  }
}

export const logCopilotChat = async (plantId = null, userMsg, botReply, toolUsed) => {
  const targetPlantId = plantId || getCurrentPlantId()
  if (!isFirebaseConfigured) {
    return { success: false, error: 'Firestore not configured' }
  }
  try {
    const chatCol = collection(db, `plants/${targetPlantId}/copilot_history`)
    await addDoc(chatCol, {
      user: userMsg,
      bot: botReply,
      tool: toolUsed || null,
      timestamp: serverTimestamp(),
    })
    return { success: true }
  } catch (err) {
    return { success: false, error: err.message }
  }
}
