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

// Read credentials from .env or fallback to developer demo config
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyDemoKeyUrjaMind2026RajkotFoundry",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "urjamind-energy.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "urjamind-energy",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "urjamind-energy.appspot.com",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "102938475612",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:102938475612:web:abcdef1234567890",
}

// Initialize Firebase safely
export const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp()
export const auth = getAuth(app)
export const db = getFirestore(app)
export const storage = getStorage(app)
export const googleProvider = new GoogleAuthProvider()

// ── Auth Helpers ─────────────────────────────────────────────────────────────
export const loginWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, googleProvider)
    return { success: true, user: result.user }
  } catch (err) {
    console.warn("Firebase Google login error:", err)
    return { success: false, error: err.message }
  }
}

export const loginWithEmail = async (email, password) => {
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
export const uploadBillDocument = async (file, plantId = "plant_1") => {
  try {
    const timestamp = Date.now()
    const storageRef = ref(storage, `bills/${plantId}/${timestamp}_${file.name}`)
    const snapshot = await uploadBytes(storageRef, file)
    const downloadUrl = await getDownloadURL(snapshot.ref)
    return { success: true, downloadUrl, path: snapshot.ref.fullPath }
  } catch (err) {
    console.warn("Firebase storage upload error (using local API fallback):", err)
    return { success: false, error: err.message }
  }
}

// ── Firestore Helpers ────────────────────────────────────────────────────────
export const savePlantRecord = async (plantId, data) => {
  try {
    const plantRef = doc(db, "plants", String(plantId))
    await setDoc(plantRef, { ...data, updatedAt: serverTimestamp() }, { merge: true })
    return { success: true }
  } catch (err) {
    console.warn("Firestore save error:", err)
    return { success: false, error: err.message }
  }
}

export const logCopilotChat = async (plantId, userMsg, botReply, toolUsed) => {
  try {
    const chatCol = collection(db, `plants/${plantId}/copilot_history`)
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
