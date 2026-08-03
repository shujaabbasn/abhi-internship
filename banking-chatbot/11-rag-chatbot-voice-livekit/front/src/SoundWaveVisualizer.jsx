import {useEffect,useRef} from 'react'

export default function SoundWaveVisualizer({stream,color='#0095ff'}) {
  const canvasRef=useRef(null)

  useEffect(()=>{
    const canvas=canvasRef.current
    const ctx=canvas.getContext('2d')
    let audioContext,analyser,source,dataArray,animationFrameId

    if(stream) {
      audioContext=new (window.AudioContext||window.webkitAudioContext)()
      analyser=audioContext.createAnalyser()
      analyser.fftSize=64
      source=audioContext.createMediaStreamSource(stream)
      source.connect(analyser)
      dataArray=new Uint8Array(analyser.frequencyBinCount)
    }

    const barCount=6
    const barWidth=5
    const gap=7

    function draw() {
      ctx.clearRect(0,0,canvas.width,canvas.height)
      if(analyser) analyser.getByteFrequencyData(dataArray)

      for(let i=0;i<barCount;i++) {
        const value=dataArray?dataArray[i*4]:0
        const height=Math.max(4,(value/255)*canvas.height)
        ctx.fillStyle=color
        ctx.fillRect(i*(barWidth+gap),(canvas.height-height)/2,barWidth,height)
      }
      animationFrameId=requestAnimationFrame(draw)
    }
    draw()

    return ()=>{
      cancelAnimationFrame(animationFrameId)
      if(source) source.disconnect()
      if(audioContext && audioContext.state!=='closed') audioContext.close()
    }
  },[stream,color])

  return <canvas ref={canvasRef} width={80} height={32} />
}