import {useState} from 'react'

function App() {
  const [message,setMessage]=useState('')
  const [history,setHistory]=useState([])

  async function sendMessage() {
    const response=await fetch('http://localhost:8000/chat',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:message})
    })
    const data=await response.json()
    setHistory([...history,{user:message,bot:data.reply}])
    setMessage('')
  }

  function handleKey(e) {
    if(e.key==='Enter') {
      sendMessage()
    }
  }

  return (
    <div style={{padding:'20px',maxWidth:'600px',margin:'0 auto'}}>
      <h1>Abhi Banking Assistant</h1>
      <div style={{border:'1px solid #ccc',height:'400px',overflowY:'auto',padding:'10px',marginBottom:'10px'}}>
        {history.map((entry,index)=>(
          <div key={index}>
            <p><strong>You:</strong> {entry.user}</p>
            <p><strong>Bot:</strong> {entry.bot}</p>
          </div>
        ))}
      </div>
      <input
        style={{width:'80%',padding:'8px'}}
        type="text"
        value={message}
        onChange={(e)=>setMessage(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Type a message and press Enter"
      />
      <button style={{padding:'8px 16px',marginLeft:'8px'}} onClick={sendMessage}>Send</button>
    </div>
  )
}

export default App
