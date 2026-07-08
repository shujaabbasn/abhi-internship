import {useState,useRef} from 'react'
import {Toaster} from 'react-hot-toast'
import toast from 'react-hot-toast'
import AdminPage from './AdminPage.jsx'

const API='http://localhost:8000'

function App() {
  const [view,setView]=useState('chat')
  const [messages,setMessages]=useState([])
  const [input,setInput]=useState('')
  const [loading,setLoading]=useState(false)
  const [session,setSession]=useState({
    pending_fields:{},
    pending_intent:null,
    missing_fields:[]
  })
  const [audioEnabled,setAudioEnabled]=useState(false)
  const [lastMessage,setLastMessage]=useState('')
  const [listening,setListening]=useState(false)
  const micRef=useRef(null)

  function stopVoiceInput() {
    micRef.current?.stop()
  }

  function startVoiceInput() {
    const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition
    const recognition=new SpeechRecognition()
    recognition.lang='en-US'
    recognition.interimResults=true
    recognition.continuous=true

    let finalTranscript=''
    let silenceTimer=null

    function resetSilenceTimer() {
      if(silenceTimer) clearTimeout(silenceTimer)
      silenceTimer=setTimeout(()=>recognition.stop(),2000)
    }

    recognition.onresult=(event)=>{
      let interim=''
      for(let i=event.resultIndex;i<event.results.length;i++) {
        if(event.results[i].isFinal) {
          finalTranscript+=event.results[i][0].transcript
        } else {
          interim+=event.results[i][0].transcript
        }
      }
      setInput(finalTranscript+interim)
      resetSilenceTimer()
    }

    recognition.onend=()=>{
      setListening(false)
      if(silenceTimer) clearTimeout(silenceTimer)
      if(finalTranscript.trim()) sendMessage(finalTranscript)
    }

    recognition.onerror=(event)=>{
      setListening(false)
      if(silenceTimer) clearTimeout(silenceTimer)
      if(event.error==='not-allowed') {
        toast.error('mic access denied')
      } else if(event.error==='no-speech') {
        toast.error('no speech detected')
      } else {
        toast.error('voice input error')
      }
    }

    micRef.current=recognition
    recognition.start()
    setListening(true)
  }

  async function speakMessage(text) {
    if(!audioEnabled) return
    try {
      const response=await fetch(API+'/speak',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({text:text})
      })
      if(!response.ok) {
        toast.error('audio request failed')
        return
      }
      const audioBlob=await response.blob()
      const audioUrl=URL.createObjectURL(audioBlob)
      const audio=new Audio(audioUrl)
      await audio.play()
    } catch(err) {
      toast.error('could not play audio: '+err.message)
    }
  }

  async function sendMessage(overrideText) {
    const textToSend=overrideText!==undefined?overrideText:input
    if (!textToSend.trim()) return
    const userMessage={role:'user',text:textToSend}
    setMessages(prev=>[...prev,userMessage])
    setLastMessage(textToSend)
    setInput('')
    setLoading(true)

    try {
      const response=await fetch(API+'/chat',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:textToSend,session:session})
      })
      const data=await response.json()

      if(!response.ok) {
        toast.error('error')
        return
      }

      setSession(data.session)
      const botMessage={role:'bot',text:data.message}
      setMessages(prev=>[...prev,botMessage])
      speakMessage(data.message)
    } catch(err) {
      toast.error('could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if(e.key==='Enter') sendMessage()
    if(e.key==='ArrowUp' && !input) setInput(lastMessage)
  }

  if(view==='admin') {
    return (
      <div>
        <Toaster position="top-right" />
        <AdminPage goToChat={()=>setView('chat')} />
      </div>
    )
  }

  return (
    <div style={{display:'flex',flexDirection:'column',height:'100vh',width:'800px',margin:'0 auto',padding:'20px',boxSizing:'border-box',overflow:'hidden'}}>
      <Toaster position="top-right" />
      <div style={{marginBottom:'16px',flexShrink:0,display:'flex',justifyContent:'space-between',alignItems:'baseline'}}>
        <h1 style={{margin:0,fontSize:'32px'}}>Abhi Assistant</h1>
        <div style={{display:'flex',gap:'16px',alignItems:'baseline'}}>
          <a href="#" style={{fontSize:'13px',color:'#ffffff'}} onClick={(e)=>{e.preventDefault();setAudioEnabled(!audioEnabled)}}>
            {audioEnabled?'Audio: On':'Audio: Off'}
          </a>
          <a href="#" style={{fontSize:'13px',color:'#ffffff'}} onClick={(e)=>{e.preventDefault();setView('admin')}}>Manage Intents</a>
        </div>
      </div>

      <div style={{height:'1000px',overflowY:'auto',border:'1px solid #ffffff',borderRadius:'8px',padding:'16px',display:'flex',flexDirection:'column',gap:'10px',marginBottom:'12px'}}>
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
        {loading&&(
          <div style={{display:'flex',alignItems:'flex-end',gap:'8px'}}>
            <div style={{padding:'10px 14px',borderRadius:'12px',backgroundColor:'#ffffff',color:'#000000'}}>
              ...
            </div>
          </div>
        )}
      </div>
      <div style={{display:'flex',gap:'8px',flexShrink:0}}>
      <textarea
        style={{
          flex:1,
          padding:'10px',
          borderRadius:'8px',
          border:'1px solid #ffffff',
          fontSize:'15px',
          resize:'none',
        }}
        placeholder="Type a message..."
        value={input}
        onChange={(e)=>setInput(e.target.value)}
        onKeyDown={handleKey}
        disabled={loading}
      />
        <button
          style={{padding:'10px 20px',borderRadius:'10px',backgroundColor:listening?'#ff0000':'#0095ff',color:'white',cursor:'pointer',fontSize:'15px'}}
          onClick={listening?stopVoiceInput:startVoiceInput}
          disabled={loading}>
          {listening?'Stop':'Mic'}
        </button>
        <button
          style={{padding:'10px 20px',borderRadius:'10px',backgroundColor:'#0095ff',color:'white',cursor:'pointer',fontSize:'15px'}}
          onClick={()=>sendMessage()}
          disabled={loading}>
          Send
        </button>
      </div>
    </div>
  )
}
export default App


//props,components
// button for intents
//fields using json or comma seoperated
//dynamic workflows??