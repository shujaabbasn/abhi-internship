import {useState,useEffect} from 'react'
import toast from 'react-hot-toast'

const API='http://localhost:8001'

function AdminPage({goToChat}) {
  const [intents,setIntents]=useState([])
  const [funcs,setFuncs]=useState([])
  const [name,setName]=useState('')
  const [description,setDescription]=useState('')
  const [fieldsText,setFieldsText]=useState('')
  const [exampleQuestion,setExampleQuestion]=useState('')
  const [exampleValuesText,setExampleValuesText]=useState('')

  const [ttsEngines,setTtsEngines]=useState([])
  const [ttsEngineEn,setTtsEngineEn]=useState('piper')
  const [ttsVoiceEn,setTtsVoiceEn]=useState('en_US-bryce-medium')
  const [ttsEngineUr,setTtsEngineUr]=useState('piper')
  const [ttsVoiceUr,setTtsVoiceUr]=useState('ur_PK-fasih-medium')
  const [ttsSpeed,setTtsSpeed]=useState(1.0)
  const [ttsTesting,setTtsTesting]=useState(false)

  async function loadIntents() {
    const response=await fetch(API+'/intents')
    const data=await response.json()
    setIntents(data)
  }

  async function loadFuncs() {
    const response=await fetch(API+'/funcs')
    const data=await response.json()
    setFuncs(data)
  }

  async function loadTtsEngines() {
    try {
      const response=await fetch(API+'/tts/engines')
      const data=await response.json()
      setTtsEngines(data)
    } catch(err) {
      console.error('could not load tts engines',err)
    }
  }

  async function loadTtsSettings() {
    try {
      const response=await fetch(API+'/tts/settings')
      const data=await response.json()
      setTtsEngineEn(data.engine_en||'piper')
      setTtsVoiceEn(data.voice_en||'en_US-bryce-medium')
      setTtsEngineUr(data.engine_ur||'piper')
      setTtsVoiceUr(data.voice_ur||'ur_PK-fasih-medium')
      setTtsSpeed(data.speed||1.0)
    } catch(err) {
      console.error('could not load tts settings',err)
    }
  }

  useEffect(()=>{
    loadIntents()
    loadFuncs()
    loadTtsEngines()
    loadTtsSettings()
  },[])

  async function addIntent() {
    if(!name.trim()||!description.trim()) {
      toast.error('Name and description are required')
      return
    }
    const required_fields=fieldsText.split(',').map(f=>f.trim()).filter(f=>f.length>0)
    const exampleValues=exampleValuesText.split(',').map(f=>f.trim()).filter(f=>f.length>0)
    const example_fields={}
    required_fields.forEach((field,index)=>{
      if(exampleValues[index]) example_fields[field]=exampleValues[index]
    })

    const response=await fetch(API+'/intents',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name,description,required_fields,example_question:exampleQuestion,example_fields})
    })
    const data=await response.json()

    if(!response.ok) {
      toast.error(data.detail||'Error')
      return
    }

    toast.success(data.message)
    setName('')
    setDescription('')
    setFieldsText('')
    setExampleQuestion('')
    setExampleValuesText('')
    loadIntents()
    loadFuncs()
  }

  async function removeIntent(intentName) {
    const response=await fetch(API+'/intents/'+intentName,{method:'DELETE'})
    const data=await response.json()
    if(!response.ok) {
      toast.error(data.detail||'Error')
      return
    }
    toast.success(data.message)
    loadIntents()
  }

  async function saveTtsSettings() {
    const response=await fetch(API+'/tts/settings',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({engine_en:ttsEngineEn,voice_en:ttsVoiceEn,engine_ur:ttsEngineUr,voice_ur:ttsVoiceUr,speed:ttsSpeed})
    })
    const data=await response.json()
    if(!response.ok) {
      toast.error(data.detail||'Error')
      return
    }
    toast.success(data.message)
  }

  async function testTtsVoice(language) {
    setTtsTesting(true)
    try {
      await saveTtsSettings()
      const testText=language==='ur'?'آپ کا اکاؤنٹ بیلنس 1000 روپے ہے':'This is a test message from your banking assistant.'
      const response=await fetch(API+'/speak',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({text:testText,language:language})
      })
      if(!response.ok) {
        toast.error('test failed')
        return
      }
      const audioBlob=await response.blob()
      const audioUrl=URL.createObjectURL(audioBlob)
      const audio=new Audio(audioUrl)
      await audio.play()
    } catch(err) {
      toast.error('could not play test audio: '+err.message)
    } finally {
      setTtsTesting(false)
    }
  }

  function getEnginesForLanguage(language) {
    return ttsEngines.filter(e=>e.languages.includes(language))
  }

  function getVoiceOptions(engineName,language) {
    const engineData=ttsEngines.find(e=>e.name===engineName)
    if(!engineData||!engineData.voices||!engineData.voices[language]) return []
    return Object.keys(engineData.voices[language])
  }

  return (
    <div style={{width:'800px',margin:'0 auto',padding:'20px',boxSizing:'border-box'}}>
      <a href="#" style={{fontSize:'14px',color:'#ffffff'}} onClick={(e)=>{e.preventDefault();goToChat()}}>Back to chat</a>
      <h1 style={{margin:0,fontSize:'32px'}}>Manage Intents</h1>
      <p style={{fontSize:'13px',color:'#ffffff'}}>
        The intent name must exactly match a function already written in backend_logic.py. Available functions: {funcs.join(', ')}
      </p>
      <div style={{display:'flex',flexDirection:'column',gap:'8px',marginTop:'12px'}}>
        <textarea
          style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',resize:'none'}}
          placeholder="Intent name"
          value={name}
          onChange={(e)=>setName(e.target.value)}
        />
        <textarea
          style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',resize:'none'}}
          placeholder="Description"
          value={description}
          onChange={(e)=>setDescription(e.target.value)}
        />
        <textarea
          style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',resize:'none'}}
          placeholder="Required fields, comma separated"
          value={fieldsText}
          onChange={(e)=>setFieldsText(e.target.value)}
        />
        <textarea
          style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',resize:'none'}}
          placeholder="Example question"
          value={exampleQuestion}
          onChange={(e)=>setExampleQuestion(e.target.value)}
        />
        <textarea
          style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',resize:'none'}}
          placeholder="Example values for the fields above, comma separated, same order"
          value={exampleValuesText}
          onChange={(e)=>setExampleValuesText(e.target.value)}
        />
        <button
          style={{padding:'10px 20px',borderRadius:'8px',backgroundColor:'#179eff',color:'white',border:'none',cursor:'pointer',fontSize:'15px'}}
          onClick={addIntent}>
          Save
        </button>
      </div>

      <div style={{marginTop:'24px',display:'flex',flexDirection:'column',gap:'28px'}}>
        {intents.map(intent=>(
          <div key={intent.name} style={{display:'flex',justifyContent:'space-between',alignItems:'center',paddingBottom:'10px'}}>
            <div style={{color:'#ffffff'}}>
              <b>{intent.name}</b>-{intent.description}
              <div style={{fontSize:'13px',color:'#ffffff'}}>
                {intent.required_fields.join(', ')||'no fields'}
              </div>
              {intent.example_question && (
                <div style={{fontSize:'13px',color:'#ffffff'}}>
                  example: "{intent.example_question}"
                </div>
              )}
            </div>
            <button
              style={{padding:'6px 12px',borderRadius:'6px',backgroundColor:'#ffffff',color:'black',border:'none',cursor:'pointer',fontSize:'13px'}}
              onClick={()=>removeIntent(intent.name)}>
              Delete
            </button>
          </div>
        ))}
      </div>

      <h1 style={{margin:'32px 0 0 0',fontSize:'32px'}}>TTS Settings</h1>
      <div style={{display:'flex',flexDirection:'column',gap:'8px',marginTop:'12px'}}>
        <div style={{display:'flex',flexDirection:'column',gap:'4px'}}>
          <label style={{fontSize:'13px',color:'#ffffff'}}>English Engine</label>
          <select
            style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',backgroundColor:'#1a1a1a',color:'#ffffff'}}
            value={ttsEngineEn}
            onChange={(e)=>{
              const newEngine=e.target.value
              setTtsEngineEn(newEngine)
              const options=getVoiceOptions(newEngine,'en')
              if(options.length>0) setTtsVoiceEn(options[0])
            }}>
            {getEnginesForLanguage('en').map(engine=>(
              <option key={engine.name} value={engine.name}>{engine.label}</option>
            ))}
          </select>
        </div>

        <div style={{display:'flex',flexDirection:'column',gap:'4px'}}>
          <label style={{fontSize:'13px',color:'#ffffff'}}>English Voice</label>
          <select
            style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',backgroundColor:'#1a1a1a',color:'#ffffff'}}
            value={ttsVoiceEn}
            onChange={(e)=>setTtsVoiceEn(e.target.value)}>
            {getVoiceOptions(ttsEngineEn,'en').map(voice=>(
              <option key={voice} value={voice}>{voice}</option>
            ))}
          </select>
        </div>

        <div style={{display:'flex',flexDirection:'column',gap:'4px'}}>
          <label style={{fontSize:'13px',color:'#ffffff'}}>Urdu Engine</label>
          <select
            style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',backgroundColor:'#1a1a1a',color:'#ffffff'}}
            value={ttsEngineUr}
            onChange={(e)=>{
              const newEngine=e.target.value
              setTtsEngineUr(newEngine)
              const options=getVoiceOptions(newEngine,'ur')
              if(options.length>0) setTtsVoiceUr(options[0])
            }}>
            {getEnginesForLanguage('ur').map(engine=>(
              <option key={engine.name} value={engine.name}>{engine.label}</option>
            ))}
          </select>
        </div>

        <div style={{display:'flex',flexDirection:'column',gap:'4px'}}>
          <label style={{fontSize:'13px',color:'#ffffff'}}>Urdu Voice</label>
          <select
            style={{padding:'10px',borderRadius:'8px',border:'1px solid #ffffff',fontSize:'15px',backgroundColor:'#1a1a1a',color:'#ffffff'}}
            value={ttsVoiceUr}
            onChange={(e)=>setTtsVoiceUr(e.target.value)}>
            {getVoiceOptions(ttsEngineUr,'ur').map(voice=>(
              <option key={voice} value={voice}>{voice}</option>
            ))}
          </select>
        </div>

        <div style={{display:'flex',flexDirection:'column',gap:'4px'}}>
          <label style={{fontSize:'13px',color:'#ffffff'}}>Speed: {ttsSpeed.toFixed(1)}x</label>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            value={ttsSpeed}
            onChange={(e)=>setTtsSpeed(parseFloat(e.target.value))}
            style={{width:'100%'}}
          />
        </div>

        <div style={{display:'flex',gap:'8px'}}>
          <button
            style={{padding:'10px 20px',borderRadius:'8px',backgroundColor:'#179eff',color:'white',border:'none',cursor:'pointer',fontSize:'15px'}}
            onClick={saveTtsSettings}>
            Save
          </button>
          <button
            style={{padding:'10px 20px',borderRadius:'8px',backgroundColor:'#444444',color:'white',border:'none',cursor:'pointer',fontSize:'15px'}}
            onClick={()=>testTtsVoice('en')}
            disabled={ttsTesting}>
            {ttsTesting?'Playing...':'Test English'}
          </button>
          <button
            style={{padding:'10px 20px',borderRadius:'8px',backgroundColor:'#444444',color:'white',border:'none',cursor:'pointer',fontSize:'15px'}}
            onClick={()=>testTtsVoice('ur')}
            disabled={ttsTesting}>
            {ttsTesting?'Playing...':'Test Urdu'}
          </button>
        </div>
      </div>

      <div style={{marginTop:'24px',padding:'16px',borderRadius:'8px',border:'1px solid #333333'}}>
        <div style={{fontSize:'13px',color:'#aaaaaa'}}>
          EN: <b>{ttsEngineEn}</b> / <b>{ttsVoiceEn}</b> | UR: <b>{ttsEngineUr}</b> / <b>{ttsVoiceUr}</b> | Speed: <b>{ttsSpeed.toFixed(1)}x</b>
        </div>
      </div>
    </div>
  )
}
export default AdminPage