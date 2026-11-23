import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ShellProvider } from './components/layout/ShellProvider'
import { ToastProvider } from './components/ui/Toast'
import { ThemeProvider } from './theme/ThemeProvider'
import App from './App.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <ToastProvider>
          <ShellProvider>
            <App />
          </ShellProvider>
        </ToastProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
)
