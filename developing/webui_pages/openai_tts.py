# encoding: utf-8
# @author: DHL
# @file: stt
# @time: 2024/5/17 下午2:14
# from dotenv import load_dotenv
import os
# load_dotenv()

api_key = "sk-1v9Jq3F5DhtvGrLlhHwQdq1AujILC4yP17KJPjI3YZkVubeC"
base_url = "https://api.chatanywhere.tech/v1"

from openai import OpenAI

def openai_tts(text3, saving_path3):
    """
    :param text3: 输入文本
    :param saving_path3: 完整的保存路径
    :return: 完整的保存路径
    """
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.audio.speech.create(
        model="tts-1-hd",
        voice="onyx",
        input=text3,
    )
    response.stream_to_file(saving_path3)

    return saving_path3

if __name__ == '__main__':
    text = "学校前身是创建于1950年的沈阳轻工业高级职业学校，1956年迁至青岛。1958年经山东省人民政府批准组建为山东化工学院，开始了正式举办高等教育的历程。1984年经教育部批准更名为青岛化工学院，1998年由化学工业部划转到山东省，二零零一年青岛工艺美术学校并入。二零零二年经教育部批准更名为青岛科技大学。"
    saving_path = "result.wav"
    path = openai_tts(text, saving_path)
    print(path)