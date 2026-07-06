import {useState} from 'react'
import toast from 'react-hot-toast'

const API='http://localhost:8000'

function SearchUser() {
  const [searchName,setSearchName]=useState('')
  const [searchResult,setSearchResult]=useState(null)

  async function searchUser() {
    setSearchResult(null)
    const response=await fetch(API+'/search?name='+searchName)
    const data=await response.json()
    if(response.ok) {
      setSearchResult(data)
    } else {
      toast.error(data.detail)
    }
  }

  return (
    <div>
      <h1>Search User</h1>
      <input placeholder="Enter username" value={searchName} onChange={(e)=>setSearchName(e.target.value)} />
      <button onClick={searchUser}>Search</button>
      {searchResult && (
        <div style={{marginTop:'20px'}}>
          <p>Username: {searchResult.username}</p>
          <p>Age: {searchResult.age}</p>
          <p>Role: {searchResult.role}</p>
          <p>School: {searchResult.school}</p>
        </div>
      )}
    </div>
  )
}

export default SearchUser
