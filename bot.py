import asyncio
import logging

from telegram import Update
from telegram.error import NetworkError, RetryAfter, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# التوكن الجديد للبوت
TOKEN = "9027534730:AAEp3p__lVUrdDZ3l6xCWfczTSURuPJdrfg"

# الآيدي الخاص بممثل الشعبة
ADMIN_ID = 5889017650

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# تم تصحيح name إلى __name__ هنا
logger = logging.getLogger(__name__)


# إرسال مع إعادة المحاولة
async def send_retry(function, **kwargs):
  for attempt in range(6):
    try:
      return await function(**kwargs)

    except RetryAfter as e:
      delay = e.retry_after
      if hasattr(delay, "total_seconds"):
        delay = delay.total_seconds()

      logger.warning("Telegram rate limit. Waiting.")
      await asyncio.sleep(float(delay) + 1)

    except NetworkError as e:
      delay = min(2**attempt, 60)
      logger.warning("Network error: %s. Retry in %s seconds", e, delay)
      await asyncio.sleep(delay)

  raise NetworkError("All sending attempts failed")


# أمر البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  if not user or not update.message:
    return

  if user.id == ADMIN_ID:
    welcome_msg = (
        "أهلاً بك يا بطل (ممثل الشعبة).\n"
        "البوت جاهز لاستلام رسائل وصور وفيديوهات الطلاب."
    )
  else:
    welcome_msg = (
        "تــم تفعـــيل البــوت بنـجـاح ✅️\n"
        "عــزيـزي الـطالـــب اصبــح بمكــانـك الان ارســال\n"
        "           (المقتــرحات و الاســـئلة)\n\n"
        "تــنبية ⚠️ اذا تجــاوز عــدد ايـام غيـابـك الـ6 "
        "ايام فسـوف يتــم حظــرك نهــائــياً مـن الخــدمـة ."
    )

  await send_retry(update.message.reply_text, text=welcome_msg)


# استقبال الرسائل والردود
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  message = update.message

  if not user or not message:
    return

  chat_id = user.id

  # ==========================
  # رد ممثل الشعبة على الطالب
  # ==========================
  if chat_id == ADMIN_ID:
    if not message.reply_to_message:
      return

    original = message.reply_to_message
    replied_msg = original.text or original.caption or ""

    if "ID: " not in replied_msg:
      await send_retry(
          message.reply_text, text="⚠️ يجب عمل Reply على رسالة الطالب الأصلية."
      )
      return

    try:
      target_id = int(replied_msg.split("ID: ", 1)[1].splitlines()[0].strip())
    except (ValueError, IndexError):
      await send_retry(
          message.reply_text, text="⚠️ تعذر قراءة آيدي الطالب من الرسالة."
      )
      return

    student_name = "عزيزي الطالب"

    for line in replied_msg.splitlines():
      if "الاسم: " in line:
        student_name = line.replace("الاسم: ", "", 1).strip()
        break

    reply_body = message.text or message.caption or ""

    formatted_reply = (
        "          «بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ»\n\n"
        f"الـــى الطـالــــب : {student_name}\n\n"
        f"{reply_body}\n\n"
        "المبــرمـــج : @hassouni_96\n"
        "نـتمنـى لـكم يومـاً سعيـداً"
    )

    try:
      if message.text:
        await send_retry(
            context.bot.send_message, chat_id=target_id, text=formatted_reply
        )

      elif message.photo:
        await send_retry(
            context.bot.send_photo,
            chat_id=target_id,
            photo=message.photo[-1].file_id,
            caption=formatted_reply,
        )

      elif message.video:
        await send_retry(
            context.bot.send_video,
            chat_id=target_id,
            video=message.video.file_id,
            caption=formatted_reply,
        )

      else:
        await send_retry(
            message.reply_text, text="⚠️ نوع الرد غير مدعوم حالياً."
        )
        return

      await send_retry(message.reply_text, text="✅ تم إرسال الرد للطالب بنجاح!")

    except TelegramError:  # تم تصحيح الإزاحة هنا
      logger.exception("Failed to send admin reply")

      try:
        await send_retry(
            message.reply_text,
            text=(
                "⚠️ تعذر إرسال الرد بسبب مشكلة اتصال. حاول مجدداً بعد قليل."
            ),
        )
      except TelegramError:
        logger.exception("Could not notify admin")

    return

  # ==========================
  # استقبال رسائل الطلاب
  # ==========================
  student_name = user.full_name

  try:
    if message.photo:
      await send_retry(
          context.bot.send_photo,
          chat_id=ADMIN_ID,
          photo=message.photo[-1].file_id,
          caption=(
              f"📩 صورة جديدة من طالب:\nالاسم: {student_name}\nID: {chat_id}"
          ),
      )

    elif message.video:
      await send_retry(
          context.bot.send_video,
          chat_id=ADMIN_ID,
          video=message.video.file_id,
          caption=(
              f"📩 فيديو جديد من طالب:\nالاسم: {student_name}\nID: {chat_id}"
          ),
      )

    elif message.text:
      forward_text = (
          f"📩 رسالة جديدة من طالب:\n"
          f"الاسم: {student_name}\n"
          f"ID: {chat_id}\n\n"
          f"النص: {message.text}"
      )

      await send_retry(
          context.bot.send_message, chat_id=ADMIN_ID, text=forward_text
      )

    else:
      return

    await send_retry(
        message.reply_text,
        text="✅ تم إرسال مشاركتك إلى ممثل الشعبة بنجاح، سيتم الرد قريباً.",
    )

  except TelegramError:
    logger.exception("Failed to process student message")


# تسجيل الأخطاء العامة
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
  logger.error("Unhandled bot error", exc_info=context.error)


# تشغيل البوت
def main():
  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(MessageHandler(~filters.COMMAND, handle_message))
  app.add_error_handler(error_handler)

  logger.info("Student representative bot started")

  app.run_polling(poll_interval=1, timeout=30, bootstrap_retries=-1)


# تم تصحيح الشرط الأخير هنا ليصبح صحيحاً
if __name__ == "__main__":
  main()
