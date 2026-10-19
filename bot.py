import os
import asyncio
import requests
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# === МОДЕЛИ (Llama заменена на DeepSeek, так как она теперь платная) ===
MODELS = {
    "llama": "deepseek/deepseek-r1:free",
    "gemini": "google/gemini-2.0-flash-lite-preview-02-05:free",
    "deepseek": "deepseek/deepseek-r1:free"
}

user_models = {} 

SYSTEM_PROMPT = """Ты — Nexus_AI, экспертный ИИ-ассистент по программированию. Твой создатель — @sigmatsch.
Твоя главная цель — писать идеальный код на Lua (Roblox/Delta Script), Python и JavaScript.

ПРАВИЛА:
1. Ты пишешь только рабочий код. Если просят скрипт для Delta Script — используй правильный API Roblox.
2. Всегда оформляй код в Markdown-блоки (например, ```lua).
3. Никакой воды. Только факты и код.
4. Если тебя спрашивают, кто тебя создал, отвечай: "Меня создал @sigmatsch".
"""

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, я <b>Nexus_AI</b>! 🤖\n"
        f"Я умею писать код на Lua (Delta Script), Python и JS.\n\n"
        f"Чтобы сменить нейросеть, напиши /model"
    )

@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text="🦙 Llama 3.3", callback_data="model_llama")],
        [InlineKeyboardButton(text="✨ Gemini (Универсал)", callback_data="model_gemini")],
        [InlineKeyboardButton(text="🧠 DeepSeek (Для логики)", callback_data="model_deepseek")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выбери нейросеть для общения:", reply_markup=markup)

@dp.callback_query(F.data.startswith("model_"))
async def set_model(callback: types.CallbackQuery):
    model_key = callback.data.split("_")[1]
    user_models[callback.from_user.id] = MODELS[model_key]
    
    names = {"llama": "Llama 3.3", "gemini": "Gemini", "deepseek": "DeepSeek"}
    await callback.message.edit_text(f"✅ Модель изменена на <b>{names[model_key]}</b>!")
    await callback.answer()

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    current_model = user_models.get(user_id, MODELS["llama"])
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://t.me", 
        "X-Title": "Nexus_AI Telegram Bot",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": current_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.text}
        ]
    }
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_answer = result["choices"][0]["message"]["content"]
            
            if len(ai_answer) > 4000:
                for i in range(0, len(ai_answer), 4000):
                    await message.answer(ai_answer[i:i+4000])
            else:
                await message.answer(ai_answer)
        else:
            await message.answer(f"❌ Ошибка OpenRouter: {response.status_code}\n{response.text}")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


# === ВЕБ-СЕРВЕР ДЛЯ RENDER ===
async def web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running!"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Веб-сервер запущен на порту {port}")

async def main():
    asyncio.create_task(web_server())
    await asyncio.sleep(2) 
    
    print("🚀 Бот Nexus_AI запущен...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
