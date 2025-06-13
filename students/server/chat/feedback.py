from fastapi import Body
from configs import logger, log_verbose
from server.utils import BaseResponse
from server.db.repository import feedback_message_to_db
import datetime

def chat_feedback(
        message_id: str = Body("", max_length=32, description="聊天记录id"),
        score: int = Body(0, max=100, description="用户评分，满分100，越大表示评价越高"),
        reason: str = Body("", description="用户评分理由，比如不符合事实等")
):
    try:
        # 原数据库存储逻辑
        feedback_message_to_db(message_id, score, reason)

        # 新增：写入日志文件（追加模式，带时间戳）
        log_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if score == 0:
            score = "满意"
        else:
            score = "不满意"
        log_content = f"[{log_time}] message_id: {message_id}, score: {score}, reason: {reason}\n"

        # 写入日志文件（使用utf-8编码，避免乱码）
        with open("feedback.log", "a", encoding="utf-8") as log_file:
            log_file.write(log_content)

    except Exception as e:
        msg = f"反馈聊天记录出错： {e}"
        logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e if log_verbose else None)
        return BaseResponse(code=500, msg=msg)

    return BaseResponse(code=200, msg=f"已反馈聊天记录 {message_id}")
