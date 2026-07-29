import {useState,useRef} from 'react'
import {Toaster} from 'react-hot-toast'
import toast from 'react-hot-toast'
import AdminPage from './AdminPage.jsx'

const API='http://localhost:8001'
const SILENCE_DURATION_MS=2000
const NOISE_FLOOR_CALIBRATION_MS=400
const SILENCE_MARGIN_ABOVE_NOISE_FLOOR=0.015

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
  const audioUnlockedRef=useRef(false)

  function unlockAudio() {
    if(audioUnlockedRef.current) return
    const silence=new Audio('data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=')
    silence.play().catch(()=>{})
    audioUnlockedRef.current=true
  }

  function stopVoiceInput() {
    if(micRef.current && micRef.current.state!=='inactive') {
      micRef.current.stop()
    }
  }

  async function startVoiceInput() {
    try {
      const stream=await navigator.mediaDevices.getUserMedia({audio:true})
      const mediaRecorder=new MediaRecorder(stream)
      const audioChunks=[]

      //silence detection via web audio api rms, auto-stops recording after a few seconds of quiet
      //calibrates against this mic/room's own noise floor instead of a fixed guessed threshold
      const audioContext=new (window.AudioContext||window.webkitAudioContext)()
      const source=audioContext.createMediaStreamSource(stream)
      const analyser=audioContext.createAnalyser()
      analyser.fftSize=512
      source.connect(analyser)

      const bufferLength=analyser.fftSize
      const dataArray=new Uint8Array(bufferLength)

      const recordingStart=Date.now()
      let noiseFloor=null
      let silenceStart=Date.now()
      let animationFrameId

      const getRms=()=>{
        analyser.getByteTimeDomainData(dataArray)
        let sumSquares=0
        for(let i=0;i<bufferLength;i++) {
          const normalized=(dataArray[i]-128)/128
          sumSquares+=normalized*normalized
        }
        return Math.sqrt(sumSquares/bufferLength)
      }

      const checkSilence=()=>{
        if(mediaRecorder.state==='inactive') return

        const rms=getRms()
        const elapsedSinceStart=Date.now()-recordingStart

        if(elapsedSinceStart<NOISE_FLOOR_CALIBRATION_MS) {
          noiseFloor=noiseFloor===null?rms:Math.max(noiseFloor,rms)
          silenceStart=Date.now()
          animationFrameId=requestAnimationFrame(checkSilence)
          return
        }

        const silenceThreshold=(noiseFloor||0)+SILENCE_MARGIN_ABOVE_NOISE_FLOOR
        if(rms>silenceThreshold) {
          silenceStart=Date.now()
        } else if(Date.now()-silenceStart>SILENCE_DURATION_MS) {
          console.log('auto-stop: rms',rms.toFixed(4),'threshold',silenceThreshold.toFixed(4))
          stopVoiceInput()
          return
        }
        animationFrameId=requestAnimationFrame(checkSilence)
      }

      mediaRecorder.ondataavailable=(event)=>{
        if(event.data.size>0) audioChunks.push(event.data)
      }

      mediaRecorder.onstop=async()=>{
        cancelAnimationFrame(animationFrameId)
        if(audioContext.state!=='closed') audioContext.close()

        const audioBlob=new Blob(audioChunks,{type:'audio/webm'})
        stream.getTracks().forEach(track=>track.stop())
        setListening(false)
        setLoading(true)

        try {
          const formData=new FormData()
          formData.append('file',audioBlob,'audio.webm')

          const response=await fetch(API+'/transcribe',{method:'POST',body:formData})
          if(!response.ok) {
            toast.error('transcription failed')
            return
          }

          const data=await response.json()
          if(data.text && data.text.trim()) {
            await sendMessage(data.text)
          } else {
            toast.error('no speech detected')
          }
        } catch(err) {
          toast.error('could not reach transcription server: '+err.message)
        } finally {
          setLoading(false)
        }
      }

      micRef.current=mediaRecorder
      mediaRecorder.start()
      setListening(true)
      checkSilence()
    } catch(err) {
      toast.error('mic access denied')
      setListening(false)
    }
  }

  async function speakMessage(text,language) {
    if(!audioEnabled) return
    try {
      const response=await fetch(API+'/speak',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({text:text,language:language||'en'})
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

      if(!response.ok) {
        toast.error('server error: '+response.status)
        return
      }

      const data=await response.json()
      setSession(data.session)
      const botMessage={role:'bot',text:data.message}
      setMessages(prev=>[...prev,botMessage])
      speakMessage(data.message,data.session.language)
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
          <button style={{fontSize:'13px',color:'#ffffff',background:'none',border:'none',padding:0,cursor:'pointer'}} onClick={()=>{if(!audioEnabled){unlockAudio()};setAudioEnabled(!audioEnabled)}}>
            {audioEnabled?'Audio: On':'Audio: Off'}
          </button>
          <button style={{fontSize:'13px',color:'#ffffff',background:'none',border:'none',padding:0,cursor:'pointer'}} onClick={()=>setView('admin')}>Manage Intents</button>
        </div>
      </div>

      <div style={{height:'1000px',overflowY:'auto',border:'1px solid #ffffff',borderRadius:'8px',padding:'16px',display:'flex',flexDirection:'column',gap:'10px',marginBottom:'12px'}}>
        {messages.map((msg,index)=>(
          <div key={index} style={{display:'flex',alignItems:'flex-end',gap:'8px',flexDirection:msg.role==='user'?'row-reverse':'row'}}>
            <div dir="auto" style={{
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