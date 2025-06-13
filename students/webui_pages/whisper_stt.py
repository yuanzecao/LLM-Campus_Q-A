# encoding: utf-8
# @author: DHL
# @file: whisper_stt
# @time: 2024/4/22 下午7:26
from streamlit_mic_recorder import mic_recorder
import streamlit as st
import io
from openai import OpenAI
import zhconv
# from dotenv import load_dotenv
import os

# Load environmenta variables from .env file
# load_dotenv()

# api_key = os.getenv('OPENAI_API_KEY')
# base_url = os.getenv('OPENAI_BASE_URL')
api_key = "sk-1v9Jq3F5DhtvGrLlhHwQdq1AujILC4yP17KJPjI3YZkVubeC"
base_url = "https://api.chatanywhere.tech/v1"
def whisper_stt(start_prompt="语音输入", stop_prompt="Stop recording", just_once=False,
                use_container_width=False, callback=None, args=(), kwargs=None, key=None):
    if 'openai_client' not in st.session_state:
        st.session_state.openai_client = OpenAI(api_key=api_key, base_url=base_url)
    if '_last_speech_to_text_transcript_id' not in st.session_state:
        st.session_state._last_speech_to_text_transcript_id = 0
    if '_last_speech_to_text_transcript' not in st.session_state:
        st.session_state._last_speech_to_text_transcript = None
    if key and not key + '_output' in st.session_state:
        st.session_state[key + '_output'] = None
    audio = mic_recorder(start_prompt=start_prompt, stop_prompt=stop_prompt, just_once=just_once,
                         use_container_width=use_container_width,format="webm", key=key)
    new_output = False
    if audio is None:
        output = None
    else:
        ID = audio['id']
        new_output = st.session_state._last_speech_to_text_transcript_id < ID
        if new_output:
            output = None
            st.session_state._last_speech_to_text_transcript_id = ID
            audio_bio = io.BytesIO(audio['bytes'])
            audio_bio.name = 'audio.webm'
            success = False
            err = 0
            while not success and err < 3:  # Retry up to 3 times in case of OpenAI server error.
                try:
                    transcript = st.session_state.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_bio,
                    )
                except Exception as e:
                    print(str(e))  # log the exception in the terminal
                    err += 1
                else:
                    success = True
                    output = transcript.text
                    st.session_state._last_speech_to_text_transcript = output
        elif not just_once:
            output = st.session_state._last_speech_to_text_transcript
        else:
            output = None

    if key:
        st.session_state[key + '_output'] = output
    if new_output and callback:
        callback(*args, **(kwargs or {}))
    if output is None:
        # 可以选择打印一个警告或日志，或者给 output 一个默认值
        print("未获取到有效的语音转文本输出，跳过转换。")
        output = ""  # 或者您可以选择其他默认值

    # 现在可以安全地尝试转换
    if output:  # 也可以不检查，因为已经处理了 None 的情况
        output = zhconv.convert(output, 'zh-hans')
    return output