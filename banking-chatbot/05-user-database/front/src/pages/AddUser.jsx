import {useState} from 'react'
import toast from 'react-hot-toast'

const API='http://localhost:8000'

function AddUser() {
  const [newUsername,setNewUsername]=useState('')
  const [newAge,setNewAge]=useState('')
  const [newRole,setNewRole]=useState('')
  const [newSchool,setNewSchool]=useState('')

  async function createUser() {
    const response=await fetch(API+'/createuser',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({username:newUsername,age:parseInt(newAge),role:newRole,school:newSchool})
    })
    const data=await response.json()
    if(response.ok) {
      toast.success(data.message)
      setNewUsername('')
      setNewAge('')
      setNewRole('')
      setNewSchool('')
    } else {
      toast.error(data.detail)
    }
  }

  return (
    <div>
      <h1>Add User</h1>
      <input placeholder="Username" value={newUsername} onChange={(e)=>setNewUsername(e.target.value)} />
      <input placeholder="Age" value={newAge} onChange={(e)=>setNewAge(e.target.value)} />
      <select value={newRole} onChange={(e)=>setNewRole(e.target.value)}>
        <option value="">Select role</option>
        <option value="student">Student</option>
        <option value="ta">TA</option>
        <option value="professor">Professor</option>
      </select>
      <input placeholder="School (optional)" value={newSchool} onChange={(e)=>setNewSchool(e.target.value)} />
      <button onClick={createUser}>Create</button>
    </div>
  )
}

export default AddUser
