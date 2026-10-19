import os
import asyncio
import requests
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

MODELS = {
    "llama": "meta-llama/llama-3.3-70b-instruct:free",
    "gemini": "google/gemini-2.0-flash-lite-preview-02-05:free",
    "deepseek": "deepseek/deepseek-r1:free"
}
user_models = {} 

SYSTEM_PROMPT = """Ты — Nexus_AI, экспертный ИИ-ассистент по программированию. Твой создатель — @sigmatsch.
ПРАВИЛА: Пиши только рабочий код на Lua (Delta), Python, JS. Оформляй в блоки. Без воды."""

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, я <b>Nexus_AI</b>! 🤖\nНапиши /model для выбора нейросети.")

@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text="🦙 Llama 3.3", callback_data="model_llama")],
        [InlineKeyboardButton(text="✨ Gemini", callback_data="model_gemini")],
        [InlineKeyboardButton(text="🧠 DeepSeek", callback_data="model_deepseek")]
    ]
    await message.answer("Выбери нейросеть:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("model_"))
async def set_model(callback: types.CallbackQuery):
    model_key = callback.data.split("_")[1]
    user_models[callback.from_user.id] = MODELS[model_key]
    await callback.message.edit_text(f"✅ Модель: <b>{model_key}</b>")
    await callback.answer()

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    current_model = user_models.get(user_id, MODELS["llama"])
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://t.me", 
        "X-Title": "Nexus_AI",
        "Content-Type": "application/json"
    }
    data = {
        "model": current_model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message.text}]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            ai_answer = response.json()["choices"][0]["message"]["content"]
            if len(ai_answer) > 4000:
                for i in range(0, len(ai_answer), 4000):
                    await message.answer(ai_answer[i:i+4000])
            else:
                await message.answer(ai_answer)
        else:
            await message.answer(f"❌ Ошибка: {response.status_code}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

# === НАДЕЖНЫЙ ВЕБ-СЕРВЕР ===
async def web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Порт {port} открыт. Веб-сервер работает.")
    # Держим сервер запущенным вечно
    await asyncio.Event().wait()

async def main():
    print("Запуск веб-сервера...")
    # Запускаем сервер и ЖДЕМ, пока он не поднимется
    await web_server() 
    
    # Если сервер запустился, запускаем бота
    print("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
