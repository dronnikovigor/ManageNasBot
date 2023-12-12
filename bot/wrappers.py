from functools import wraps

from bot import preferences


# Check if message from owner
def is_message_from_bot_owner():
    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            if update is not None and update.effective_message:
                message = update.effective_message
                if message.from_user and message.from_user.id != preferences.owner_id:
                    return
                return await func(update, context, *args, **kwargs)
            return

        return command_func

    return decorator


# Check if the chat is allowed
def is_chat_allowed():
    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            if update is not None and update.effective_message:
                message = update.effective_message
                chat_id = message.chat_id
                if chat_id != preferences.owner_id:
                    return
                return await func(update, context, *args, **kwargs)
            return

        return command_func

    return decorator
