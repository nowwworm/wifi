import os
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from sqlalchemy import select, func, update
from database.connection import async_session
from database.models import Edit
from config import ADMIN_TELEGRAM_ID
from utils.pdf_generator import generate_edits_pdf
from utils.yandex_disk import upload_file_to_yandex_disk

router = Router()

def get_admin_panel_markup() -> InlineKeyboardMarkup:
    """Returns the main admin control panel keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(text="Сформировать отчет в PDF 📄", callback_data="admin_gather")
        ],
        [
            InlineKeyboardButton(text="Статистика 📊", callback_data="admin_stats"),
            InlineKeyboardButton(text="Принятые правки 📋", callback_data="admin_list_approved")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("admin"), lambda msg: msg.from_user.id == ADMIN_TELEGRAM_ID)
@router.message(Command("start"), lambda msg: msg.from_user.id == ADMIN_TELEGRAM_ID)
async def cmd_admin_panel(message: Message):
    """Shows the admin panel to the authorized administrator."""
    text = (
        "👑 **Панель Администратора**\n\n"
        "Добро пожаловать в панель управления правками проекта **feo2sport**.\n"
        "Здесь вы можете посмотреть текущий статус или собрать все принятые правки в PDF-отчёт на Яндекс.Диск."
    )
    await message.answer(text, reply_markup=get_admin_panel_markup(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("approve:"))
async def process_approve(callback: CallbackQuery, bot: Bot):
    """Approves a client's edit."""
    edit_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        # Get edit details
        query = select(Edit).where(Edit.id == edit_id)
        result = await session.execute(query)
        edit = result.scalar_one_or_none()
        
        if not edit:
            await callback.answer("Правка не найдена в базе.", show_alert=True)
            return
            
        if edit.status != "pending":
            await callback.answer(f"Статус этой правки уже: {edit.status}", show_alert=True)
            return
            
        edit.status = "approved"
        await session.commit()
        
        client_id = edit.client_id
        text_preview = edit.text_content[:30] + "..." if edit.text_content and len(edit.text_content) > 30 else edit.text_content
        client_msg = f"Ваша правка «{text_preview or 'Изображение'}» принята в работу! ✅"

    # Notify client
    try:
        await bot.send_message(chat_id=client_id, text=client_msg)
    except Exception as e:
        print(f"Failed to notify client {client_id}: {e}")

    # Update admin message
    await callback.answer("Правка принята!")
    raw_text = callback.message.text or callback.message.caption or ""
    import html
    new_text = html.escape(raw_text) + "\n\n<b>Статус: Принята ✅</b>"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=new_text, reply_markup=None, parse_mode="HTML")
    else:
        await callback.message.edit_text(text=new_text, reply_markup=None, parse_mode="HTML")

@router.callback_query(F.data.startswith("reject:"))
async def process_reject(callback: CallbackQuery, bot: Bot):
    """Rejects a client's edit."""
    edit_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        # Get edit details
        query = select(Edit).where(Edit.id == edit_id)
        result = await session.execute(query)
        edit = result.scalar_one_or_none()
        
        if not edit:
            await callback.answer("Правка не найдена в базе.", show_alert=True)
            return
            
        if edit.status != "pending":
            await callback.answer(f"Статус этой правки уже: {edit.status}", show_alert=True)
            return
            
        edit.status = "rejected"
        await session.commit()
        
        client_id = edit.client_id
        text_preview = edit.text_content[:30] + "..." if edit.text_content and len(edit.text_content) > 30 else edit.text_content
        client_msg = f"Ваша правка «{text_preview or 'Изображение'}» отклонена. ❌"

    # Notify client
    try:
        await bot.send_message(chat_id=client_id, text=client_msg)
    except Exception as e:
        print(f"Failed to notify client {client_id}: {e}")

    # Update admin message
    await callback.answer("Правка отклонена.")
    raw_text = callback.message.text or callback.message.caption or ""
    import html
    new_text = html.escape(raw_text) + "\n\n<b>Статус: Отклонена ❌</b>"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=new_text, reply_markup=None, parse_mode="HTML")
    else:
        await callback.message.edit_text(text=new_text, reply_markup=None, parse_mode="HTML")

@router.callback_query(F.data == "admin_stats")
async def process_stats(callback: CallbackQuery):
    """Displays stats about the edits in the database."""
    async with async_session() as session:
        # Count statuses
        query = select(Edit.status, func.count(Edit.id)).group_by(Edit.status)
        result = await session.execute(query)
        stats = dict(result.all())
        
    pending = stats.get("pending", 0)
    approved = stats.get("approved", 0)
    rejected = stats.get("rejected", 0)
    archived = stats.get("archived", 0)
    
    text = (
        "📊 **Статистика правок**\n\n"
        f"• Ожидают модерации (pending): `{pending}`\n"
        f"• Приняты (approved): `{approved}`\n"
        f"• Отклонены (rejected): `{rejected}`\n"
        f"• Выгружены в архив (archived): `{archived}`\n\n"
        f"Всего правок в базе: `{pending + approved + rejected + archived}`"
    )
    
    await callback.message.answer(text, reply_markup=get_admin_panel_markup(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_list_approved")
async def process_list_approved(callback: CallbackQuery):
    """Lists all approved edits waiting to be exported."""
    async with async_session() as session:
        query = select(Edit).where(Edit.status == "approved").order_by(Edit.created_at)
        result = await session.execute(query)
        approved_edits = result.scalars().all()
        
    if not approved_edits:
        await callback.message.answer("📋 Нет принятых правок, ожидающих сборки.", reply_markup=get_admin_panel_markup())
        await callback.answer()
        return
        
    text = "📋 **Принятые правки (ожидают сборки):**\n\n"
    for i, edit in enumerate(approved_edits, 1):
        username = f"@{edit.client_username}" if edit.client_username else f"ID {edit.client_id}"
        has_img = "📸 Скриншот" if edit.image_path else "✍ Текст"
        text_preview = edit.text_content[:50] + "..." if edit.text_content and len(edit.text_content) > 50 else (edit.text_content or "[Без описания]")
        text += f"{i}. **{username}** [{has_img}]:\n   _{text_preview}_\n\n"
        
    await callback.message.answer(text, reply_markup=get_admin_panel_markup(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_gather")
async def process_gather_changes(callback: CallbackQuery, bot: Bot):
    """Generates PDF report, uploads to Yandex Disk, archives edits, and deletes temp files."""
    # 1. Fetch approved edits
    async with async_session() as session:
        query = select(Edit).where(Edit.status == "approved").order_by(Edit.created_at)
        result = await session.execute(query)
        approved_edits = result.scalars().all()
        
    if not approved_edits:
        await callback.answer("Нет принятых правок для сборки!", show_alert=True)
        return
        
    await callback.message.answer("⏳ Начинаю генерацию PDF и выгрузку на Яндекс.Диск...")
    await callback.answer()
    
    # 2. Generate PDF locally
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_filename = f"feo2sport_edits_{timestamp}.pdf"
    pdf_local_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), pdf_filename)
    
    try:
        await generate_edits_pdf(approved_edits, pdf_local_path)
        
        # 3. Upload to Yandex.Disk
        # Folder on disk can be named feo2sport_edits
        yandex_folder = "feo2sport_edits"
        remote_path = await upload_file_to_yandex_disk(pdf_local_path, pdf_filename, yandex_folder)
        
        # 4. Send document to Admin in chat
        await bot.send_document(
            chat_id=ADMIN_TELEGRAM_ID,
            document=FSInputFile(pdf_local_path),
            caption=f"📄 Сборка правок от {datetime.now().strftime('%d.%m.%Y %H:%M')}\nУспешно загружено на Яндекс.Диск в `/Приложения/FeoSportBot/{remote_path}`"
        )
        
        # 5. Archive edits and delete local image downloads
        async with async_session() as session:
            for edit in approved_edits:
                # Update status
                edit.status = "archived"
                
                # Delete local downloaded image to save space
                if edit.image_path and os.path.exists(edit.image_path):
                    try:
                        os.remove(edit.image_path)
                    except Exception as clean_err:
                        print(f"Error removing file {edit.image_path}: {clean_err}")
                        
            await session.commit()
            
        await callback.message.answer(
            f"✅ Успешно обработано правок: {len(approved_edits)}.\n"
            f"Отчёт загружен на Яндекс.Диск и отправлен в чат."
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Произошла ошибка во время сборки или выгрузки:\n`{str(e)}`", parse_mode="Markdown")
        print(f"Gather changes error: {e}")
        
    finally:
        # 6. Cleanup local PDF file
        if os.path.exists(pdf_local_path):
            try:
                os.remove(pdf_local_path)
            except Exception as e:
                print(f"Failed to remove local PDF: {e}")
