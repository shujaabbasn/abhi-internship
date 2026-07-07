import {useState} from 'react'
import {Toaster} from 'react-hot-toast'
import toast from 'react-hot-toast'

const API='http://localhost:8000'

function App() {
  const [messages,setMessages]=useState([])
  const [input,setInput]=useState('')
  const [loading,setLoading]=useState(false)
  const [session,setSession]=useState({
    pending_fields:{},
    pending_intent:null,
    missing_fields:[]
  })

  async function sendMessage() {
    if (!input.trim()) return
    const userMessage={role:'user',text:input}
    setMessages(prev=>[...prev,userMessage])
    setInput('')
    setLoading(true)

    try {
      const response=await fetch(API+'/chat',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:input,session:session})
      })
      const data=await response.json()

      if(!response.ok) {
        toast.error('Error')
        return
      }

      setSession(data.session)
      const botMessage={role:'bot',text:data.message}
      setMessages(prev=>[...prev,botMessage])
    } catch(err) {
      toast.error('Could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if(e.key==='Enter') sendMessage()
  }

  return (
    <div style={{display:'flex',flexDirection:'column',height:'100vh',width:'800px',margin:'0 auto',padding:'20px',boxSizing:'border-box',overflow:'hidden'}}>
      <Toaster position="top-right" />
      <div style={{marginBottom:'16px',flexShrink:0}}>
        <h1 style={{margin:0,fontSize:'32px'}}>Abhi Assistant</h1>
      </div>

      <div style={{height:'1000px',overflowY:'auto',border:'1px solid #ccc',borderRadius:'8px',padding:'16px',display:'flex',flexDirection:'column',gap:'10px',marginBottom:'12px'}}>
        {messages.map((msg,index)=>(
          <div key={index} style={{display:'flex',alignItems:'flex-end',gap:'8px',flexDirection:msg.role==='user'?'row-reverse':'row'}}>
            <div style={{
              maxWidth:'75%',
              padding:'10px 14px',
              borderRadius:'12px',
              backgroundColor:msg.role==='user'?'#58b3f4':'#ffffff',
              color:msg.role==='user'?'white':'black',
              whiteSpace:'pre-wrap'
            }}>
              {msg.text}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{display:'flex',alignItems:'flex-end',gap:'8px'}}>
            <div style={{padding:'10px 14px',borderRadius:'12px',backgroundColor:'#f0f0f0',color:'#999'}}>
              ...
            </div>
          </div>
        )}
      </div>
      <div style={{display:'flex',gap:'8px',flexShrink:0}}>
        <input
          style={{flex:1,padding:'10px',borderRadius:'8px',border:'1px solid #ccc',fontSize:'15px'}}
          placeholder="Type a message..."
          value={input}
          onChange={(e)=>setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button
          style={{padding:'10px 20px',borderRadius:'8px',backgroundColor:'#0095ff',color:'white',border:'none',cursor:'pointer',fontSize:'15px'}}
          onClick={sendMessage}
          disabled={loading}>
          Send
        </button>
      </div>
    </div>
  )
}

export default App


//props,components
//button to add intent
//takes name,definition and fields
//fields using json or comma seoperated
//give an input box for function (text area) for longer inputs
//for now, have a function written for any intent we add. this would follow dynamic workflows generally but not using for now as too complex
//dynamic workflows??