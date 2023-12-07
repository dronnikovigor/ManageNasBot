from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ConversationHandler


def get_last_n_characters(input_string, n):
    if n >= len(input_string):
        return input_string
    else:
        return input_string[-n:]


# Stop conversation
async def cancel_conv(update: Update, _) -> int:
    await update.message.reply_text("Canceled", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
