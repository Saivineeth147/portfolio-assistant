import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Upload, Send, X, FileText, MessageCircle, Key, CheckCircle, AlertCircle, Loader2, Zap } from 'lucide-react'

// Generate session ID once
const SESSION_ID = crypto.randomUUID()

// Star Background Component
function StarField() {
  return (
    <div className="star-field">
      {Array.from({ length: 100 }, (_, i) => (
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
  const [provider, setProvider] = useState('groq')  // 'groq' or 'huggingface'
  const [models, setModels] = useState([])  // Available models
  const [selectedModel, setSelectedModel] = useState('')  // Selected model ID
  const [loadingModels, setLoadingModels] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [connectionStatus, setConnectionStatus] = useState(null)  // null, 'testing', 'success', 'error'
  const [apiKeyError, setApiKeyError] = useState(null)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // Test connection handler
  const testConnection = async () => {
    if (!apiKey) return
    setConnectionStatus('testing')
    setApiKeyError(null)
    try {
      const res = await fetch('/assistant/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, api_key: apiKey })
      })
      const data = await res.json()
      if (data.models?.length > 0) {
        setModels(data.models)
        setSelectedModel(data.models[0].id)
        setConnectionStatus('success')
        localStorage.setItem(`${provider}_api_key`, apiKey)
      } else {
        setConnectionStatus('error')
        setApiKeyError('No models found. Check your API key.')
      }
    } catch (err) {
      setConnectionStatus('error')
      setApiKeyError('Connection failed: ' + err.message)
    }
  }

  // Reset models when provider changes
  useEffect(() => {
    setModels([])
    setSelectedModel('')
    setConnectionStatus(null)
    setApiKeyError(null)
  }, [provider])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
        body: JSON.stringify({
          message: userMessage,
          provider: provider,
          model: selectedModel || null,
          api_key: apiKey || null
        })
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

        {/* Settings Panel */}
        <div className="settings-panel">
          {/* Provider Card */}
          <div className="settings-card">
            <div className="card-header">
              <Zap size={16} />
              <span>Provider</span>
            </div>
            <select
              className="form-select"
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value)
                setConnectionStatus(null)
                setModels([])
              }}
            >
              <option value="groq">Groq (Fast)</option>
              <option value="huggingface">HuggingFace</option>
            </select>

            <div className="form-group">
              <label className="form-label">
                Model
                {loadingModels && <Loader2 size={12} className="spinner" />}
                {models.length > 0 && <span className="model-count">({models.length})</span>}
              </label>
              <select
                className="form-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={models.length === 0}
              >
                {models.length > 0 ? (
                  models.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))
                ) : (
                  <option value="">Enter API key to load models</option>
                )}
              </select>
            </div>
          </div>

          {/* API Key Card */}
          <div className="settings-card">
            <div className="card-header">
              <Key size={16} />
              <span>API Key</span>
              {connectionStatus === 'success' && (
                <span className="status-badge success">
                  <CheckCircle size={12} /> Connected
                </span>
              )}
            </div>
            <input
              type="password"
              className={`form-input ${apiKeyError ? 'error' : ''}`}
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value)
                setConnectionStatus(null)
              }}
              placeholder={`Paste your ${provider === 'groq' ? 'Groq' : 'HuggingFace'} API key`}
            />
            {apiKeyError ? (
              <span className="status-text error">
                <AlertCircle size={12} /> {apiKeyError}
              </span>
            ) : (
              <span className={`status-text ${models.length > 0 ? 'success' : ''}`}>
                {models.length > 0
                  ? `✓ ${models.length} models loaded`
                  : 'Models will load when you test connection'}
              </span>
            )}
            <button
              className="test-connection-btn"
              onClick={testConnection}
              disabled={!apiKey || connectionStatus === 'testing'}
            >
              {connectionStatus === 'testing' ? (
                <><Loader2 size={14} className="spinner" /> Testing...</>
              ) : connectionStatus === 'error' ? (
                <><AlertCircle size={14} /> Retry</>
              ) : connectionStatus === 'success' ? (
                <><CheckCircle size={14} /> Connected!</>
              ) : (
                <><Zap size={14} /> Test Connection</>
              )}
            </button>
            <a
              className="api-key-link"
              href={provider === 'groq' ? 'https://console.groq.com/keys' : 'https://huggingface.co/settings/tokens'}
              target="_blank"
              rel="noopener noreferrer"
            >
              🔑 Get your {provider === 'groq' ? 'Groq' : 'HuggingFace'} API key →
            </a>
          </div>
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
                          {[...new Set(msg.sources.map(s => s.source))].map((source, i) => (
                            <span key={i} className="source-chip">{source}</span>
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
