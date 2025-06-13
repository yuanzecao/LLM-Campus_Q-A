import streamlit as st
from webui_pages.utils import *
from streamlit_option_menu import option_menu
from webui_pages.dialogue.dialogue import dialogue_page, chat_box
from webui_pages.knowledge_base.knowledge_base import knowledge_base_page
import os
import sys
from configs import VERSION
from server.utils import api_address
import base64

api = ApiRequest(base_url=api_address())

def sidebar_bg(side_bg):
    side_bg_ext = 'png'

    st.markdown(
        f"""
      <style>
      [data-testid="stSidebar"] > div:first-child {{
          background: url(data:image/{side_bg_ext};base64,{base64.b64encode(open(side_bg, "rb").read()).decode()});
      }}
      </style>
      """,
        unsafe_allow_html=True,)


def main_bg(main_bg):
    main_bg_ext = "png"
    st.markdown(
        f"""
         <style>
         .stApp {{
             background: url(data:image/{main_bg_ext};base64,{base64.b64encode(open(main_bg, "rb").read()).decode()});
             background-size: cover
         }}
         </style>
         """,
        unsafe_allow_html=True
    )
    st.markdown("""
        <style>
            .reportview-container {
                margin-top: -2em;
            }
            #MainMenu {visibility: hidden;}
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            #stDecoration {display:none;}
        </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    is_lite = "lite" in sys.argv

    st.set_page_config(
        "青岛科技大学AI辅导员",
        os.path.join("img", "Haiyan1.png"),
        initial_sidebar_state="expanded",
        menu_items={
            'About': f"""欢迎使用 青岛科技大学AI辅导员 {VERSION}！"""
        }
    )

    # 设置背景照片
    main_bg(".\img\\background(1).png")
    # 设置侧边栏背景照片
    sidebar_bg('.\img\\background(2).png')

    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Zhi+Mang+Xing&display=swap');

            .zhi-mang-xing-regular {
              font-family: "Zhi Mang Xing", cursive;
              font-weight: 400;
              text-align: center;
              font-size: 70px;
              font-style: normal;
            }
        </style>
        <div class="zhi-mang-xing-regular">
            青岛科技大学AI辅导员
        </div>
    """, unsafe_allow_html=True)

    st.image(
        os.path.join(
            "img",
            "Haiyan.png"
        ),
        use_column_width=True
    )
    pages = {
        "对话": {
            "icon": "chat",
            "func": dialogue_page,
        },
        # "知识库管理": {
        #     "icon": "hdd-stack",
        #     "func": knowledge_base_page,
        # },
    }

    with st.sidebar:
        st.image(
            os.path.join(
                "img",
                "QUST_logo.png"
            ),
            use_column_width=True
        )
        st.image(
            os.path.join(
                "img",
                "Data_school.png"
            ),
            use_column_width=True
        )
        # st.caption(
        #     f"""<p align="right">当前版本：{VERSION}</p>""",
        #     unsafe_allow_html=True,
        # )
        options = list(pages)
        icons = [x["icon"] for x in pages.values()]

        default_index = 0
        selected_page = option_menu(
            "",
            options=options,
            icons=icons,
            # menu_icon="chat-quote",
            default_index=default_index,
        )

    if selected_page in pages:
        pages[selected_page]["func"](api=api, is_lite=is_lite)
