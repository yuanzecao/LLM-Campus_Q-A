import time
import dashscope
from dashscope.audio.tts import SpeechSynthesizer
import os
def dashscope_tts(text):
    dashscope.api_key='sk-5fa361805d7f4a81b107a13d37aa3cb1'
    #cosyvoice-v1/sambert-zhichu-v1
    result = SpeechSynthesizer.call(model='sambert-zhichu-v1',
                                    text=text,
                                    sample_rate=16000,
                                    format='wav')
    # 获取当前文件的绝对路径
    file_path = os.path.abspath(__file__)
    # 获取当前文件所在的目录
    directory = os.path.dirname(file_path)

    path = os.path.join(directory, 'dialogue//result.wav')
    if result.get_audio_data() is not None:
        with open(path, 'wb') as f:
            f.write(result.get_audio_data())
    #print('  get response: %s' % (result.get_response()))