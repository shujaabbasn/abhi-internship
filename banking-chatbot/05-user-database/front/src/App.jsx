import {BrowserRouter,Routes,Route,NavLink} from 'react-router-dom' //for routing
import {Toaster} from 'react-hot-toast' //toast lib, https://dev.to/connectaryal/choosing-the-right-toast-library-for-react-no-fluff-just-facts-2k5o
import AllUsers from './pages/AllUsers'
import AddUser from './pages/AddUser'
import SearchUser from './pages/SearchUser'

//display=flex needed for side by side sidebar and main page
// minHeight 100vh for full height
//flex direction column for vertical

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <div style={{display:'flex',minHeight:'100vh'}}> 
        <div style={{width:'150px',backgroundColor:'#000000',padding:'40px',display:'flex',flexDirection:'column',gap:'20px'}}>
          <h2 style={{color:'white',marginBottom:'10px'}}>Menu</h2>
          <NavLink to="/" style={({isActive})=>{
            if(isActive) {return {color:'rgb(0, 149, 255)',textDecoration:'none'}}
            else {return {color:'white',textDecoration:'none'}}
          }}>All Users</NavLink>
          <NavLink to="/add" style={({isActive})=>{
            if(isActive) {return {color:'rgb(0, 149, 255)',textDecoration:'none'}}
            else {return {color:'white',textDecoration:'none'}}
          }}>Add User</NavLink>
          <NavLink to="/search" style={({isActive})=>{
            if(isActive) {return {color:'rgb(0, 149, 255)',textDecoration:'none'}}
            else {return {color:'white',textDecoration:'none'}}
          }}>Search User</NavLink>
        </div>
        <div style={{flex:1,padding:'20px'}}>
          <Routes>
            <Route path="/" element={<AllUsers />} />
            <Route path="/add" element={<AddUser />} />
            <Route path="/search" element={<SearchUser />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App