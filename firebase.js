import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// Import other services you need, e.g.,
// import { getFirestore } from "firebase/firestore";
// import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyC5ToY8r5V_5CbOCsgeFTXlvsNfxZ8-j88",
  authDomain: "propas-7dfb1.firebaseapp.com",
  projectId: "propas-7dfb1",
  storageBucket: "propas-7dfb1.firebasestorage.app",
  messagingSenderId: "377624143656",
  appId: "1:377624143656:web:6fc6cb48cc26dfcaaf921d",
  measurementId: "G-DWDC5MWGS6"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

// Export the instances to use them in other files
export { app, analytics };