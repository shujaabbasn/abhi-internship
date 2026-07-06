import {useState,useEffect} from 'react'
import toast from 'react-hot-toast'

const API='http://localhost:8000'

function AllUsers() {
  const [allUsers,setAllUsers]=useState([])
  const [editUser,setEditUser]=useState(null)
  const [editAge,setEditAge]=useState('')
  const [editSchool,setEditSchool]=useState('')

  useEffect(()=>{
    getAllUsers()
  },[])

  async function getAllUsers() {
    const response=await fetch(API+'/allusers')
    const data=await response.json()
    setAllUsers(data.users)
  }

  async function deleteUser(name) {
    if(!window.confirm('Delete user '+name+'?')) return
    const response=await fetch(API+'/deleteuser?name='+name,{method:'DELETE'})
    const data=await response.json()
    if(response.ok) {
      toast.success(data.message)
      getAllUsers()
    } else {
      toast.error(data.detail)
    }
  }

  function openEdit(user) {
    setEditUser(user)
    setEditAge(user.age)
    setEditSchool(user.school||'')
  }

  async function saveEdit() {
    const request1=await fetch(API+'/updateage?name='+editUser.username+'&new_age='+editAge,{method:'PUT'})
    const request2=await fetch(API+'/updateschool?name='+editUser.username+'&school='+editSchool,{method:'PUT'})
    if(request1.ok && request2.ok) {
      toast.success('updated successfully')
      setEditUser(null)
      getAllUsers()
    } else {
      toast.error('update failed')
    }
  }

  return (
    <div>
      <h1>All Users</h1>
      {allUsers.length>0 && (
        <table border="1" cellPadding="10" style={{borderCollapse:'collapse',width:'100%',marginTop:'10px'}}>
          <thead>
            <tr>
              <th>Username</th>
              <th>Age</th>
              <th>Role</th>
              <th>School</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {allUsers.map((user,index)=>(
              <tr key={index}>
                <td>{user.username}</td>
                <td>{user.age}</td>
                <td>{user.role}</td>
                <td>{user.school}</td>
                <td>
                  <button onClick={()=>openEdit(user)}>Edit</button>
                  <button onClick={()=>deleteUser(user.username)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {editUser && (
        <div style={{position:'fixed',top:0,left:0,width:'100%',height:'100%',backgroundColor:'rgba(0, 0, 0, 0.7)',display:'flex',alignItems:'center',justifyContent:'center'}}>
          <div style={{backgroundColor:'white',padding:'30px',borderRadius:'8px',minWidth:'300px'}}>
            <h3>Editing {editUser.username}</h3>
            <input placeholder="Age" value={editAge} onChange={(e)=>setEditAge(e.target.value)} />
            <input placeholder="School" value={editSchool} onChange={(e)=>setEditSchool(e.target.value)} />
            <button onClick={saveEdit}>Save</button>
            <button onClick={()=>setEditUser(null)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default AllUsers
