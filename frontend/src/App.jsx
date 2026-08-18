import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar/Sidebar'
import DocumentsPage from './pages/DocumentsPage/DocumentsPage';
import ChatPage from './pages/ChatPage/ChatPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="app-content">
          <Routes>
            <Route path="/" element={<DocumentsPage />} />
            <Route path="/chat/:conversationId" element={<ChatPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;