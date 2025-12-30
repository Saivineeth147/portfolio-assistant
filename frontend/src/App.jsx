import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Upload, Send, X, FileText, MessageCircle, Key } from 'lucide-react'

// Generate session ID once
const SESSION_ID = crypto.randomUUID()

// Star Background Component
function StarField() {
  return (
    <div className="star-field">
      {Array.from({ length: 30 }, (_, i) => (
        <div key={i} className="star" />
      ))}
    </div>
  )
}

// Main App
export default function App() {
  const [documents, setDocuments] = useState([])
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Cleanup session on tab close
  useEffect(() => {
    const cleanup = () => {
      navigator.sendBeacon('/assistant/session/end', JSON.stringify({ session_id: SESSION_ID }))
    }
    window.addEventListener('beforeunload', cleanup)
    return () => window.removeEventListener('beforeunload', cleanup)
  }, [])

  // API helpers
  const headers = {
    'X-Session-ID': SESSION_ID,
    'Content-Type': 'application/json'
  }

  // Upload document
  const handleUpload = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    try {
      const res = await fetch('/assistant/upload', {
        method: 'POST',
        headers: { 'X-Session-ID': SESSION_ID },
        body: formData
      })
      
      if (!res.ok) {
        const error = await res.json()
        alert(error.detail || 'Upload failed')
        return
      }
      
      const doc = await res.json()
      setDocuments(prev => [...prev, doc])
    } catch (err) {
      console.error('Upload error:', err)
      alert('Failed to upload file')
    } finally {
      setUploading(false)
    }
  }

  // Delete document
  const handleDelete = async (docId) => {
    try {
      await fetch(`/assistant/documents/${docId}`, {
        method: 'DELETE',
        headers
      })
      setDocuments(prev => prev.filter(d => d.id !== docId))
    } catch (err) {
      console.error('Delete error:', err)
    }
  }

  // Send message
  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const res = await fetch('/assistant/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: userMessage })
      })

      const data = await res.json()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        sources: data.sources
      }])
    } catch (err) {
      console.error('Chat error:', err)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.'
      }])
    } finally {
      setLoading(false)
    }
  }

  // Handle key press
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => setDragOver(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) handleUpload(file)
  }

  return (
    <>
      <StarField />
      
      <div className="app-container">
        {/* Header */}
        <header className="header">
          <h1>🤖 Portfolio Assistant</h1>
          <p>Upload your documents and ask questions</p>
        </header>

        {/* API Key Input */}
        <div className="api-key-section">
          <label>
            <Key size={16} />
            Groq API Key
          </label>
          <input
            type="password"
            className="api-key-input"
            placeholder="Enter your Groq API key (optional if set on server)"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>

        {/* Upload Zone */}
        <div
          className={`upload-zone ${dragOver ? 'dragover' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload size={32} />
          <p>{uploading ? 'Uploading...' : 'Drag & drop files here or click to browse'}</p>
          <p className="formats">Supported: PDF, DOCX, TXT, Markdown, JSON</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md,.json"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </div>

        {/* Document List */}
        {documents.length > 0 && (
          <div className="documents">
            {documents.map(doc => (
              <div key={doc.id} className="doc-chip">
                <FileText size={14} />
                <span className="type">{doc.type}</span>
                <span>{doc.filename}</span>
                <button onClick={() => handleDelete(doc.id)}>
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Chat Container */}
        <div className="chat-container">
          <div className="messages">
            {messages.length === 0 ? (
              <div className="welcome-message">
                <MessageCircle size={48} />
                <h3>Start a conversation</h3>
                <p>Upload documents above, then ask questions about them.</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  {msg.role === 'assistant' ? (
                    <>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                      {msg.sources?.length > 0 && (
                        <div className="sources">
                          Sources:
                          {msg.sources.map((src, i) => (
                            <span key={i} className="source-chip">{src.source}</span>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    msg.content
                  )}
                </div>
              ))
            )}
            {loading && (
              <div className="message assistant">
                <div className="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="chat-input-container">
            <textarea
              className="chat-input"
              placeholder="Ask a question about your documents..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              className="send-button"
              onClick={handleSend}
              disabled={!input.trim() || loading}
            >
              <Send size={18} />
              Send
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
