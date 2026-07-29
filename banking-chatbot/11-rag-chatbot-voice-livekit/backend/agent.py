import os
from dotenv import load_dotenv
import tempfile
import io
import wave
import requests

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, llm, stt
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.utils import merge_frames
from livekit.agents.utils.audio import AudioByteStream
from livekit.plugins import silero

import whisper_stt
from tts_piper import synthesize_piper

load_dotenv()
CHAT_BACKEND_URL=os.environ.get("CHAT_BACKEND_URL","http://localhost:8001")


class WhisperSTT(stt.STT):
    def __init__(self):
        super().__init__(capabilities=stt.STTCapabilities(streaming=False,interim_results=False))

    async def _recognize_impl(self,buffer,*,language=None,conn_options=DEFAULT_API_CONNECT_OPTIONS):
        frame=merge_frames(buffer)
        fd, wav_path=tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            with open(wav_path,"wb") as f:
                f.write(frame.to_wav_bytes())
            text,detected_language=whisper_stt.transcribe_audio(wav_path)
        finally:
            os.remove(wav_path)
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language=detected_language,text=text)],
        )


class PlaceholderLLM(llm.LLM):
    #AgentSession refuses to auto-generate a reply at all unless an llm is configured, so this
    #only exists to satisfy that check. never called
    def chat(self,*,chat_ctx,tools=None,conn_options=DEFAULT_API_CONNECT_OPTIONS,**kwargs):
        raise NotImplementedError("PlaceholderLLM.chat should never be called")


class BankingAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are a banking voice assistant.")
        self._session_state = {
            "pending_intent":None,
            "pending_fields":{},
            "missing_fields":[],
            "language": "en",
        }

    async def llm_node(self, chat_ctx, tools, model_settings):
        user_message=chat_ctx.items[-1].text_content
        response=requests.post(
            f"{CHAT_BACKEND_URL}/chat",
            json={"message": user_message, "session": self._session_state},
            timeout=45,
        )
        result=response.json()
        self._session_state=result["session"]
        return result["message"]

    async def tts_node(self, text, model_settings):
        full_text=""
        async for chunk in text:
            full_text+=chunk
        if self._session_state.get("language")=="en":
            voice_file="en_US-bryce-medium.onnx"
        else:
            voice_file="ur_PK-abhibank-finetune.onnx"
        wav_bytes=synthesize_piper(full_text,voice_file,speed=1.0)
        with wave.open(io.BytesIO(wav_bytes),"rb") as wav_file:
            sample_rate=wav_file.getframerate()
            num_channels=wav_file.getnchannels()
            pcm_data=wav_file.readframes(wav_file.getnframes())
        audio_stream=AudioByteStream(sample_rate=sample_rate,num_channels=num_channels)
        for frame in audio_stream.push(pcm_data):
            yield frame
        for frame in audio_stream.flush():
            yield frame


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session=AgentSession(
        vad=silero.VAD.load(),
        stt=WhisperSTT(),
        llm=PlaceholderLLM(),
        turn_handling={"turn_detection": "vad"},
    )

    await session.start(agent=BankingAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))