import streamlit as st
from webui_pages.utils import *
from webui_pages.whisper_stt import *
from streamlit_chatbox import *
from streamlit_modal import Modal
from datetime import datetime
import os
import re
import time
from configs import (TEMPERATURE, HISTORY_LEN, PROMPT_TEMPLATES, LLM_MODELS,
                     DEFAULT_KNOWLEDGE_BASE, DEFAULT_SEARCH_ENGINE, SUPPORT_AGENT_MODEL)
from server.knowledge_base.utils import LOADER_DICT
import uuid
from typing import List, Dict
from streamlit_float import *
from webui_pages.dashscope_tts import *
chat_box = ChatBox(
    assistant_avatar=os.path.join(
        "img",
        "Haiyan1.png"
    ),
    user_avatar =os.path.join(
        "img",
        "students.png"
    )
)


def get_messages_history(history_len: int, content_in_expander: bool = False) -> List[Dict]:
    '''
    返回消息历史。
    content_in_expander控制是否返回expander元素中的内容，一般导出的时候可以选上，传入LLM的history不需要
    '''

    def filter(msg):
        content = [x for x in msg["elements"] if x._output_method in ["markdown", "text"]]
        if not content_in_expander:
            content = [x for x in content if not x._in_expander]
        content = [x.content for x in content]

        return {
            "role": msg["role"],
            "content": "\n\n".join(content),
        }

    return chat_box.filter_history(history_len=history_len, filter=filter)


@st.cache_data
def upload_temp_docs(files, _api: ApiRequest) -> str:
    '''
    将文件上传到临时目录，用于文件对话
    返回临时向量库ID
    '''
    return _api.upload_temp_docs(files).get("data", {}).get("id")


def parse_command(text: str, modal: Modal) -> bool:
    '''
    检查用户是否输入了自定义命令，当前支持：
    /new {session_name}。如果未提供名称，默认为“会话X”
    /del {session_name}。如果未提供名称，在会话数量>1的情况下，删除当前会话。
    /clear {session_name}。如果未提供名称，默认清除当前会话
    /help。查看命令帮助
    返回值：输入的是命令返回True，否则返回False
    '''
    if m := re.match(r"/([^\s]+)\s*(.*)", text):
        cmd, name = m.groups()
        name = name.strip()
        conv_names = chat_box.get_chat_names()
        if cmd == "help":
            modal.open()
        elif cmd == "new":
            if not name:
                i = 1
                while True:
                    name = f"会话{i}"
                    if name not in conv_names:
                        break
                    i += 1
            if name in st.session_state["conversation_ids"]:
                st.error(f"该会话名称 “{name}” 已存在")
                time.sleep(1)
            else:
                st.session_state["conversation_ids"][name] = uuid.uuid4().hex
                st.session_state["cur_conv_name"] = name
        elif cmd == "del":
            name = name or st.session_state.get("cur_conv_name")
            if len(conv_names) == 1:
                st.error("这是最后一个会话，无法删除")
                time.sleep(1)
            elif not name or name not in st.session_state["conversation_ids"]:
                st.error(f"无效的会话名称：“{name}”")
                time.sleep(1)
            else:
                st.session_state["conversation_ids"].pop(name, None)
                chat_box.del_chat_name(name)
                st.session_state["cur_conv_name"] = ""
        elif cmd == "clear":
            chat_box.reset_history(name=name or None)
        return True
    return False


def dialogue_page(api: ApiRequest, is_lite: bool = False):
    st.session_state.setdefault("conversation_ids", {})
    st.session_state["conversation_ids"].setdefault(chat_box.cur_chat_name, uuid.uuid4().hex)
    st.session_state.setdefault("file_chat_id", None)
    default_model = api.get_default_llm_model()[0]

    if not chat_box.chat_inited:
        st.toast(
            f"欢迎使用 `青岛科技大学AI辅导员`! \n\n"
            f"当前运行的模型`{default_model}`, 您可以开始提问了."
        )
        chat_box.init_session()

    # 弹出自定义命令帮助信息
    modal = Modal("自定义命令", key="cmd_help", max_width="500")
    if modal.is_open():
        with modal.container():
            cmds = [x for x in parse_command.__doc__.split("\n") if x.strip().startswith("/")]
            st.write("\n\n".join(cmds))

    with st.sidebar:
        # 多会话
        conv_names = list(st.session_state["conversation_ids"].keys())
        index = 0
        if st.session_state.get("cur_conv_name") in conv_names:
            index = conv_names.index(st.session_state.get("cur_conv_name"))
        conversation_name = "default"
        chat_box.use_chat_name(conversation_name)
        conversation_id = st.session_state["conversation_ids"][conversation_name]

        def on_mode_change():
            mode = st.session_state.dialogue_mode
            text = f"已切换到 {mode} 模式。"
            if mode == "知识库问答":
                cur_kb = st.session_state.get("selected_kb")
                if cur_kb:
                    text = f"{text} 当前知识库： `{cur_kb}`。"
            st.toast(text)

        dialogue_modes = ["LLM 对话",
                          "知识库问答",
                          "简历修改",
                          "联网搜索",
                          # "自定义Agent问答",
                          ]
        dialogue_mode = st.selectbox("请选择对话模式：",
                                     dialogue_modes,
                                     index=0,
                                     on_change=on_mode_change,
                                     key="dialogue_mode",
                                     )

        def on_llm_change():
            if llm_model:
                config = api.get_model_config(llm_model)
                if not config.get("online_api"):  # 只有本地model_worker可以切换模型
                    st.session_state["prev_llm_model"] = llm_model
                st.session_state["cur_llm_model"] = st.session_state.llm_model

        def llm_model_format_func(x):
            if x in running_models:
                return f"{x} (Running)"
            return x

        running_models = list(api.list_running_models())

        available_models = []
        config_models = api.list_config_models()
        if not is_lite:
            for k, v in config_models.get("local", {}).items():
                if (v.get("model_path_exists")
                        and k not in running_models):
                    available_models.append(k)
        for k, v in config_models.get("online", {}).items():
            if not v.get("provider") and k not in running_models and k in LLM_MODELS:
                available_models.append(k)
        llm_models = running_models + available_models
        cur_llm_model = st.session_state.get("cur_llm_model", default_model)
        if cur_llm_model in llm_models:
            index = llm_models.index(cur_llm_model)
        else:
            index = 0
        # llm_model = st.selectbox("选择大语言模型：",
        #                          llm_models,
        #                          index,
        #                          format_func=llm_model_format_func,
        #                          on_change=on_llm_change,
        #                          key="llm_model",
        #                          )
        llm_model = 'qwen-api'
        if (st.session_state.get("prev_llm_model") != llm_model
                and not is_lite
                and not llm_model in config_models.get("online", {})
                and not llm_model in config_models.get("langchain", {})
                and llm_model not in running_models):
            with st.spinner(f"正在加载模型： {llm_model}，请勿进行操作或刷新页面"):
                prev_model = st.session_state.get("prev_llm_model")
                r = api.change_llm_model(prev_model, llm_model)
                if msg := check_error_msg(r):
                    st.error(msg)
                elif msg := check_success_msg(r):
                    st.success(msg)
                    st.session_state["prev_llm_model"] = llm_model

        index_prompt = {
            "LLM 对话": "llm_chat",
            # "自定义Agent问答": "agent_chat",
            "联网搜索": "search_engine_chat",
            "知识库问答": "knowledge_base_chat",
            "简历修改": "knowledge_base_chat",
        }
        prompt_templates_kb_list = list(PROMPT_TEMPLATES[index_prompt[dialogue_mode]].keys())
        print(prompt_templates_kb_list)
        prompt_template_name = prompt_templates_kb_list[0]
        if "prompt_template_select" not in st.session_state:
            st.session_state.prompt_template_select = prompt_templates_kb_list[0]

        def prompt_change():
            text = f"已切换为 {prompt_template_name} 模板。"
            st.toast(text)

        # prompt_template_select = st.selectbox(
        #     "请选择Prompt模板：",
        #     prompt_templates_kb_list,
        #     index=0,
        #     on_change=prompt_change,
        #     key="prompt_template_select",
        # )
        prompt_template_name = st.session_state.prompt_template_select
        temperature = 0.70
        history_len = 3

        def on_kb_change():
            st.toast(f"已加载知识库： {st.session_state.selected_kb}")

        if dialogue_mode == "知识库问答":
            with st.expander("知识库配置", True):
                kb_list = api.list_knowledge_bases()
                index = 0
                if DEFAULT_KNOWLEDGE_BASE in kb_list:
                    index = kb_list.index(DEFAULT_KNOWLEDGE_BASE)
                # selected_kb = st.selectbox(
                #     "请选择知识库：",
                #     kb_list,
                #     index=index,
                #     on_change=on_kb_change,
                #     key="selected_kb",
                # )
                kb_top_k = st.number_input("匹配知识条数：", 1, 20, 10)

                ## Bge 模型会超过1
                score_threshold = st.slider("知识匹配分数阈值：", 0.0, 2.0, float(SCORE_THRESHOLD), 0.01)
        elif dialogue_mode == "简历修改":
            with st.expander("简历修改配置", True):

                files = st.file_uploader("上传简历文件：",
                                         [i for ls in LOADER_DICT.values() for i in ls],
                                         accept_multiple_files=True,
                                         )
                kb_top_k = 3

                ## Bge 模型会超过1
                score_threshold = 1
                if st.button("开始上传", disabled=len(files) == 0):
                    st.session_state["file_chat_id"] = upload_temp_docs(files, api)


        elif dialogue_mode == "联网搜索":
            search_engine_list = api.list_search_engines()
            if DEFAULT_SEARCH_ENGINE in search_engine_list:
                index = search_engine_list.index(DEFAULT_SEARCH_ENGINE)
            else:
                index = search_engine_list.index("duckduckgo") if "duckduckgo" in search_engine_list else 0
            with st.expander("搜索引擎配置", True):
                # search_engine = st.selectbox(
                #     label="请选择搜索引擎",
                #     options=search_engine_list,
                #     index=index,
                # )
                search_engine = "duckduckgo"
                se_top_k = st.number_input("匹配搜索结果条数：", 1, 20, SEARCH_ENGINE_TOP_K)

    # Display chat messages from history on app rerun
    chat_box.output_messages()

    chat_input_placeholder = ""

    def on_feedback(
            feedback,
            message_id: str = "",
            history_index: int = -1,
    ):
        reason = feedback["text"]
        score_int = chat_box.set_feedback(feedback=feedback, history_index=history_index)
        api.chat_feedback(message_id=message_id,
                          score=score_int,
                          reason=reason)
        st.session_state["need_rerun"] = True

    feedback_kwargs = {
        "feedback_type": "thumbs",
        "optional_text_label": "欢迎反馈您打分的理由",
    }

    chat_input_container = st.container()
    with chat_input_container:
        cols = st.columns([5, 1])
        with cols[0]:
            prompt = st.chat_input(chat_input_placeholder, key="prompt")
        with cols[1]:
            prompt_button = whisper_stt("🎤", just_once=True,use_container_width=True)
    chat_input_css = float_css_helper(bottom="1rem", display="flex", justify_content="center", margin="0 auto",
                                      max_width="1000px")
    # Float button container
    chat_input_container.float(chat_input_css)

    if prompt := prompt or prompt_button:
        if parse_command(text=prompt, modal=modal):  # 用户输入自定义命令
            st.rerun()
        else:
            history = get_messages_history(history_len)
            chat_box.user_say(prompt)
            if dialogue_mode == "LLM 对话":

                chat_box.ai_say("正在思考...")
                text = ""
                message_id = ""
                r = api.chat_chat(prompt,
                                  history=history,
                                  conversation_id=conversation_id,
                                  model=llm_model,
                                  prompt_name="default1",
                                  temperature=temperature)
                for t in r:
                    if error_msg := check_error_msg(t):  # check whether error occured
                        st.error(error_msg)
                        break
                    text += t.get("text", "")
                    chat_box.update_msg(text)
                    message_id = t.get("message_id", "")

                metadata = {
                    "message_id": message_id,
                }
                chat_box.update_msg(text, streaming=False, metadata=metadata)  # 更新最终的字符串，去除光标
                chat_box.show_feedback(**feedback_kwargs,
                                       key=message_id,
                                       on_submit=on_feedback,
                                       kwargs={"message_id": message_id, "history_index": len(chat_box.history) - 1})

                dashscope_tts(text)

                # 获取当前文件的绝对路径
                file_path = os.path.abspath(__file__)
                # 获取当前文件所在的目录
                directory = os.path.dirname(file_path)
                out_video_path = os.path.join(directory, 'result.wav')
                st.audio(out_video_path, format="audio/wav", autoplay=True)

            elif dialogue_mode == "自定义Agent问答":
                if not any(agent in llm_model for agent in SUPPORT_AGENT_MODEL):
                    chat_box.ai_say([
                        f"正在思考... \n\n <span style='color:red'>该模型并没有进行Agent对齐，请更换支持Agent的模型获得更好的体验！</span>\n\n\n",
                        Markdown("...", in_expander=True, title="思考过程", state="complete"),

                    ])
                else:
                    chat_box.ai_say([
                        f"正在思考...",
                        Markdown("...", in_expander=True, title="思考过程", state="complete"),

                    ])
                text = ""
                ans = ""
                for d in api.agent_chat(prompt,
                                        history=history,
                                        model=llm_model,
                                        prompt_name=prompt_template_name,
                                        temperature=temperature,
                                        ):
                    try:
                        d = json.loads(d)
                    except:
                        pass
                    if error_msg := check_error_msg(d):  # check whether error occured
                        st.error(error_msg)
                    if chunk := d.get("answer"):
                        text += chunk
                        chat_box.update_msg(text, element_index=1)
                    if chunk := d.get("final_answer"):
                        ans += chunk
                        chat_box.update_msg(ans, element_index=0)
                    if chunk := d.get("tools"):
                        text += "\n\n".join(d.get("tools", []))
                        chat_box.update_msg(text, element_index=1)
                chat_box.update_msg(ans, element_index=0, streaming=False)
                chat_box.update_msg(text, element_index=1, streaming=False)
                dashscope_tts(text)

                # 获取当前文件的绝对路径
                file_path = os.path.abspath(__file__)
                # 获取当前文件所在的目录
                directory = os.path.dirname(file_path)
                out_video_path = os.path.join(directory, 'result.wav')
                st.audio(out_video_path, format="audio/wav", autoplay=True)
            elif dialogue_mode == "知识库问答":

                selected_kb = ""
                r = api.chat_chat(prompt,
                                  conversation_id=conversation_id,
                                  model=llm_model,
                                  prompt_name="default",
                                  temperature=temperature)
                for t in r:
                    if error_msg := check_error_msg(t):  # check whether error occured
                        st.error(error_msg)
                        break
                    selected_kb += t.get("text", "")

                if selected_kb == "self_chat":
                    chat_box.ai_say("正在思考...")
                    text = ""
                    message_id = ""
                    r = api.chat_chat(prompt,
                                      history=history,
                                      conversation_id=conversation_id,
                                      model=llm_model,
                                      prompt_name="default2",
                                      temperature=temperature)
                    for t in r:
                        if error_msg := check_error_msg(t):  # check whether error occured
                            st.error(error_msg)
                            break
                        text += t.get("text", "")
                        chat_box.update_msg(text)
                        message_id = t.get("message_id", "")

                    metadata = {
                        "message_id": message_id,
                    }
                    chat_box.update_msg(text, streaming=False, metadata=metadata)  # 更新最终的字符串，去除光标
                    dashscope_tts(text)

                    # 获取当前文件的绝对路径
                    file_path = os.path.abspath(__file__)
                    # 获取当前文件所在的目录
                    directory = os.path.dirname(file_path)
                    out_video_path = os.path.join(directory, 'result.wav')
                    st.audio(out_video_path, format="audio/wav", autoplay=True)
                else:

                    chat_box.ai_say([
                        f"正在查询知识库 `{selected_kb}` ...",
                        Markdown("...", in_expander=True, title="知识库匹配结果", state="complete"),
                    ])
                    text = ""
                    for d in api.knowledge_base_chat(prompt,
                                                     knowledge_base_name=selected_kb,
                                                     top_k=kb_top_k,
                                                     score_threshold=score_threshold,
                                                     model=llm_model,
                                                     prompt_name=selected_kb,
                                                     temperature=temperature):

                        if error_msg := check_error_msg(d):  # check whether error occured
                            st.error(error_msg)
                        elif chunk := d.get("answer"):
                            text += chunk
                            chat_box.update_msg(text, element_index=0)
                    chat_box.update_msg(text, element_index=0, streaming=False)
                    chat_box.update_msg("\n\n".join(d.get("docs", [])), element_index=1, streaming=False)
                    start = time.perf_counter()

                    dashscope_tts(text)
                    end = time.perf_counter()
                    print(f"time.perf_counter() 计时：{end - start:.9f} 秒")
                    # 获取当前文件的绝对路径
                    file_path = os.path.abspath(__file__)
                    # 获取当前文件所在的目录
                    directory = os.path.dirname(file_path)
                    out_video_path = os.path.join(directory, 'result.wav')

                    st.audio(out_video_path, format="audio/wav", autoplay=True)

            elif dialogue_mode == "简历修改":

                if st.session_state["file_chat_id"] is None:
                    st.error("请先上传简历再进行对话")
                    st.stop()

                chat_box.ai_say([
                    f"正在查询简历 `{st.session_state['file_chat_id']}` ...",
                    Markdown("...", in_expander=True, title="简历匹配结果", state="complete"),
                ])
                text = ""
                for d in api.file_chat(prompt,
                                       knowledge_id=st.session_state["file_chat_id"],
                                       top_k=kb_top_k,
                                       score_threshold=score_threshold,
                                       history=history,
                                       model=llm_model,
                                       prompt_name="Resume",
                                       temperature=temperature):
                    if error_msg := check_error_msg(d):  # check whether error occured
                        st.error(error_msg)
                    elif chunk := d.get("answer"):
                        text += chunk
                        chat_box.update_msg(text, element_index=0)
                chat_box.update_msg(text, element_index=0, streaming=False)
                chat_box.update_msg("\n\n".join(d.get("docs", [])), element_index=1, streaming=False)

                dashscope_tts(text)

                # 获取当前文件的绝对路径
                file_path = os.path.abspath(__file__)
                # 获取当前文件所在的目录
                directory = os.path.dirname(file_path)
                out_video_path = os.path.join(directory, 'result.wav')
                st.audio(out_video_path, format="audio/wav", autoplay=True)
            elif dialogue_mode == "联网搜索":

                chat_box.ai_say([
                    f"正在执行 `{search_engine}` 搜索...",
                    Markdown("...", in_expander=True, title="网络搜索结果", state="complete"),
                ])
                text = ""
                for d in api.search_engine_chat(prompt,
                                                search_engine_name=search_engine,
                                                top_k=se_top_k,
                                                history=history,
                                                model=llm_model,
                                                prompt_name=prompt_template_name,
                                                temperature=temperature,
                                                split_result=se_top_k > 1):
                    if error_msg := check_error_msg(d):  # check whether error occured
                        st.error(error_msg)
                    elif chunk := d.get("answer"):
                        text += chunk
                        chat_box.update_msg(text, element_index=0)
                chat_box.update_msg(text, element_index=0, streaming=False)
                chat_box.update_msg("\n\n".join(d.get("docs", [])), element_index=1, streaming=False)
                dashscope_tts(text)

                # 获取当前文件的绝对路径
                file_path = os.path.abspath(__file__)
                # 获取当前文件所在的目录
                directory = os.path.dirname(file_path)
                out_video_path = os.path.join(directory, 'result.wav')
                st.audio(out_video_path, format="audio/wav", autoplay=True)


    if st.session_state.get("need_rerun"):
        st.session_state["need_rerun"] = False
        st.rerun()

    now = datetime.now()
    with st.sidebar:

        cols = st.columns(2)
        export_btn = cols[0]
        if cols[1].button(
                "清空对话",
                use_container_width=True,
        ):
            chat_box.reset_history()
            st.rerun()
        st.caption(
            f"""
                <p align="center" style="color: black;">© 2025 青岛科技大学</span><br>
                <span style="color: black;">版权所有</span><br>
                <span style="color: black;">青岛科技大学数据科学学院</span><br>
                <span style="color: black;">技术支持</span><br>
                """,
            unsafe_allow_html=True,
        )

    export_btn.download_button(
        "导出记录",
        "".join(chat_box.export2md()),
        file_name=f"{now:%Y-%m-%d %H.%M}_对话记录.md",
        mime="text/markdown",
        use_container_width=True,
    )
