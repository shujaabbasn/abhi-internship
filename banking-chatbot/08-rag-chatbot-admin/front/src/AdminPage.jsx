import {useState,useEffect} from 'react'
import toast from 'react-hot-toast'

const API='http://localhost:8000'

function AdminPage({goToChat}) {
  const [intents,setIntents]=useState([])
  const [funcs,setFuncs]=useState([])
  const [name,setName]=useState('')
  const [description,setDescription]=useState('')
  const [fieldsText,setFieldsText]=useState('')
  const [exampleQuestion,setExampleQuestion]=useState('')
  const [exampleValuesText,setExampleValuesText]=useState('')

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

  useEffect(()=>{
    loadIntents()
    loadFuncs()
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

  return (
    <div style={{width:'800px',margin:'0 auto',padding:'20px',boxSizing:'border-box'}}>
      <a href="#" style={{fontSize:'14px',color:'#ffffff'}} onClick={(e)=>{e.preventDefault();goToChat()}}>Back to chat</a>
      <h1 style={{margin:0,fontSize:'32px'}}>Manage Intents</h1>
      <p style={{fontSize:'13px',color:'#ffffff'}}>
        The intent name must exactly match a function already written in backend_logic.py. Available functions: {funcs.join(', ')}
      </p>
      <div style={{display:'flex',flexDirection:'column',gap:'8px',marginTop:'12px'}}>
        <textarea
          style={{padding:'10px',borderRadius:'2px',border:'1px solid #ffffff',fontSize:'15px',resize:'none'}}
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
    </div>
  )
}
export default AdminPage