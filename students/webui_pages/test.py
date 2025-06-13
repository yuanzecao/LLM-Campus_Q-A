from streamlit_mic_recorder import mic_recorder
import streamlit as st
import os


def save_audio(audio, save_path="recorded_audio.webm"):
    if audio is not None:
        audio_bytes = audio['bytes']
        with open(save_path, "wb") as f:
            f.write(audio_bytes)
        st.success(f"音频已保存至：{os.path.abspath(save_path)}")
        return True
    return False


# 页面主逻辑
st.title("麦克风音频保存示例")
audio = mic_recorder(
    start_prompt="点击开始录音",
    stop_prompt="点击停止录音",
    format="webm",
    use_container_width=True
)

if audio:
    save_audio(audio, "my_recording.webm")
    # 可选：显示音频播放组件（仅支持部分格式）
    st.audio(audio['bytes'], format="audio/webm")
