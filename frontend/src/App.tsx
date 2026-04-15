import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { ChatPage } from './pages/ChatPage'
import { DocPage } from './pages/DocPage'
import { LibraryPage } from './pages/LibraryPage'

function App() {
  return (
    <div className="min-h-full bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-10 border-b bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/library" className="text-lg font-semibold">
            PKM 智能助手
          </Link>
          <nav className="flex gap-3 text-sm">
            <NavLink
              to="/library"
              className={({ isActive }) =>
                isActive ? 'font-semibold text-indigo-600' : 'text-slate-600 hover:text-slate-900'
              }
            >
              文库
            </NavLink>
            <NavLink
              to="/chat"
              className={({ isActive }) =>
                isActive ? 'font-semibold text-indigo-600' : 'text-slate-600 hover:text-slate-900'
              }
            >
              问答
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<LibraryPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/doc/:id" element={<DocPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
