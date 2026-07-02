import { useState } from 'react'

function App() {
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState([])

  async function sendMessage() {
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: message, language: 'english' })
    })
    const data = await response.json()
    setHistory([...history, { user: message, bot: data.reply }])
    setMessage('')
  }

  return (
    <div>
      <h1>Chat</h1>
      <div>
        {history.map((entry, index) => (
          <div key={index}>
            <p>You: {entry.user}</p>
            <p>Bot: {entry.bot}</p>
          </div>
        ))}
      </div>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type a message"
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  )
}

export default App