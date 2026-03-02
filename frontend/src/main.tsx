import React from 'react'
import ReactDOM from 'react-dom/client'
import { initFirebase } from './lib/firebase'
import App from './App'
import './index.css'

initFirebase()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
