import os
import uuid
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
from database.connection import async_session
from database.models import Edit
from config import ADMIN_TELEGRAM_ID

router = Router()

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def get_admin_markup(edit_id: int) -> InlineKeyboardMarkup:
    """Returns the inline keyboard for admin moderation."""
    keyboard = [
        [
            InlineKeyboardButton(text="Принять ✅", callback_data=f"approve:{edit_id}"),
            InlineKeyboardButton(text="Отклонить ❌", callback_data=f"reject:{edit_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(CommandStart(), lambda msg: msg.from_user.id != ADMIN_TELEGRAM_ID)
async def cmd_start_client(message: Message):
    """Greets the client and explains how to send edits."""
    text = (
        "Привет! Я бот для приёма правок по проекту **feo2sport**.\n\n"
        "Отправьте мне вашу правку:\n"
        "• Это может быть просто текст.\n"
        "• Либо прикрепите скриншот и добавьте к нему текстовое описание в подписи.\n\n"
        "Я передам ваши замечания разработчику на рассмотрение!"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(lambda msg: msg.from_user.id != ADMIN_TELEGRAM_ID)
async def process_client_edit(message: Message, bot: Bot):
    """Processes incoming edits (text and/or photos) from the client."""
    text_content = message.text or message.caption or ""
    image_path = None
    
    # Check if user sent a photo
    if message.photo:
        # Get the largest photo size
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Create a unique local filename
        ext = ".jpg"
        local_filename = f"{uuid.uuid4()}{ext}"
        image_path = os.path.join(DOWNLOADS_DIR, local_filename)
        
        # Download the file
        await bot.download(file_id, destination=image_path)
    
    # Save edit to the database
    async with async_session() as session:
        new_edit = Edit(
            client_id=message.from_user.id,
            client_username=message.from_user.username or message.from_user.first_name or "Unknown",
            text_content=text_content,
            image_path=image_path,
            status="pending"
        )
        session.add(new_edit)
        await session.commit()
        await session.refresh(new_edit)
        edit_id = new_edit.id

    # Inform client
    await message.answer("Спасибо! Ваша правка принята и отправлена на модерацию разработчику. 📥")
    
    # Forward to Admin
    import html
    import logging
    logger = logging.getLogger(__name__)
    
    safe_username = html.escape(new_edit.client_username or "Unknown")
    safe_text = html.escape(text_content or "[Без описания]")
    
    admin_caption = (
        f"📥 <b>Новая правка #{edit_id}</b>\n"
        f"<b>От:</b> {safe_username} (ID: {new_edit.client_id})\n"
        f"<b>Текст:</b> {safe_text}"
    )
    
    markup = get_admin_markup(edit_id)
    
    try:
        if image_path and os.path.exists(image_path):
            # Send photo with markup
            await bot.send_photo(
                chat_id=ADMIN_TELEGRAM_ID,
                photo=FSInputFile(image_path),
                caption=admin_caption[:1024],  # Telegram caption limit is 1024
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            # Send text message
            await bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=admin_caption,
                reply_markup=markup,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Error sending notification to admin: {e}", exc_info=True)
