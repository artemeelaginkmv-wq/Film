import asyncio
import sqlite3
import os
import re
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ТВОЙ_ТОКЕН")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5087161437"))
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "ТВОЙ_КЛЮЧ_TMDB")

# 🔗 Ссылка на будущий сайт
SITE_URL = os.environ.get("SITE_URL", "https://example.com")

# 🖼️ Картинки разделов
IMG_MAIN = os.environ.get("IMG_MAIN", "https://i.imgur.com/y5hXwu9.png")
IMG_NEW = os.environ.get("IMG_NEW", "https://i.imgur.com/tPKKbzj.jpeg")
IMG_GENRES = os.environ.get("IMG_GENRES", "https://i.imgur.com/VkFGiC3.jpeg")
IMG_COUNTRIES = os.environ.get("IMG_COUNTRIES", "https://i.imgur.com/QuLhiWY.jpeg")
IMG_SEARCH = os.environ.get("IMG_SEARCH", "https://i.imgur.com/rocsBTG.png")
IMG_ORDER = os.environ.get("IMG_ORDER", "https://i.imgur.com/MYSHR4h.jpeg")
IMG_ADMIN = os.environ.get("IMG_ADMIN", "https://i.imgur.com/ntREPaT.jpeg")
IMG_ABOUT = os.environ.get("IMG_ABOUT", "")
IMG_PROFILE = os.environ.get("IMG_PROFILE", "")
IMG_SUPPORT = os.environ.get("IMG_SUPPORT", "")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_states = {}

# ========== БАЗА ==========
def init_db():
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS films (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        genre TEXT DEFAULT 'Другое',
        country TEXT DEFAULT 'Другое',
        year TEXT DEFAULT '—',
        quality TEXT DEFAULT 'HD',
        rating_kp TEXT DEFAULT '—',
        rating_imdb TEXT DEFAULT '—',
        poster_url TEXT,
        watch_url TEXT,
        category TEXT DEFAULT 'Фильмы',
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT UNIQUE NOT NULL,
        title TEXT DEFAULT '',
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def add_film(title, description, genre, country, year, quality, rating_kp, rating_imdb, poster_url, watch_url="", category="Фильмы"):
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("""INSERT INTO films 
                 (title, description, genre, country, year, quality, rating_kp, rating_imdb, poster_url, watch_url, category)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (title, description, genre, country, year, quality, rating_kp, rating_imdb, poster_url, watch_url, category))
    conn.commit()
    conn.close()

def get_film(film_id):
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("SELECT * FROM films WHERE id = ?", (film_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_films(category=None, genre=None, country=None, limit=10, offset=0):
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    sql = "SELECT * FROM films WHERE 1=1"
    params = []
    if category and category != "Все":
        sql += " AND category = ?"; params.append(category)
    if genre and genre != "Все":
        sql += " AND genre LIKE ?"; params.append(f"%{genre}%")
    if country and country != "Все":
        sql += " AND country LIKE ?"; params.append(f"%{country}%")
    sql += " ORDER BY added_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return rows

def count_films(category=None, genre=None, country=None):
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    sql = "SELECT COUNT(*) FROM films WHERE 1=1"
    params = []
    if category and category != "Все":
        sql += " AND category = ?"; params.append(category)
    if genre and genre != "Все":
        sql += " AND genre LIKE ?"; params.append(f"%{genre}%")
    if country and country != "Все":
        sql += " AND country LIKE ?"; params.append(f"%{country}%")
    c.execute(sql, params)
    count = c.fetchone()[0]
    conn.close()
    return count

def search_films(query, limit=10, offset=0):
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("SELECT * FROM films WHERE title LIKE ? ORDER BY added_at DESC LIMIT ? OFFSET ?",
              (f"%{query}%", limit, offset))
    rows = c.fetchall()
    conn.close()
    return rows

def get_genres():
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT genre FROM films")
    rows = c.fetchall()
    conn.close()
    genres = set()
    for r in rows:
        for g in (r[0] or "").split(","):
            g = g.strip()
            if g: genres.add(g)
    return sorted(genres)

def get_countries():
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT country FROM films")
    rows = c.fetchall()
    conn.close()
    countries = set()
    for r in rows:
        for cn in (r[0] or "").split(","):
            cn = cn.strip()
            if cn: countries.add(cn)
    return sorted(countries)

def delete_film(film_id):
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("SELECT title FROM films WHERE id = ?", (film_id,))
    row = c.fetchone()
    if not row:
        conn.close(); return None
    c.execute("DELETE FROM films WHERE id = ?", (film_id,))
    conn.commit()
    conn.close()
    return row[0]

def get_channels():
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("SELECT chat_id, title FROM channels ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return [{"chat_id": r[0], "title": r[1]} for r in rows]

def add_channel(chat_id, title=""):
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO channels (chat_id, title) VALUES (?, ?)", (chat_id, title))
    conn.commit()
    conn.close()

def remove_channel(chat_id):
    conn = sqlite3.connect("films.db")
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

# ========== TMDB ==========
async def fetch_tmdb_info(title):
    if not TMDB_API_KEY or TMDB_API_KEY == "ТВОЙ_КЛЮЧ_TMDB":
        return None
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}&language=ru-RU"
            async with session.get(url) as resp:
                if resp.status != 200: return None
                data = await resp.json()
                results = data.get("results", [])
                if not results: return None
                movie_id = results[0]["id"]
            url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=ru-RU"
            async with session.get(url) as resp:
                if resp.status != 200: return None
                details = await resp.json()
            genres = ", ".join([g["name"] for g in details.get("genres", [])])
            countries = ", ".join([c["name"] for c in details.get("production_countries", [])])
            year = details.get("release_date", "")[:4]
            poster_path = details.get("poster_path")
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            return {
                "title": details.get("title", title),
                "description": details.get("overview", ""),
                "genre": genres or "Другое",
                "country": countries or "Другое",
                "year": year,
                "rating": str(details.get("vote_average", "—")),
                "poster_url": poster_url,
            }
    except Exception as e:
        print(f"Ошибка TMDB: {e}")
        return None

# ========== ПОДПИСКА ==========
async def is_subscribed(user_id):
    channels = get_channels()
    if not channels: return True, []
    not_sub = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_sub.append(ch)
        except Exception:
            not_sub.append(ch)
    return len(not_sub) == 0, not_sub

def subscribe_kb(not_sub):
    buttons = []
    for ch in not_sub:
        cid = ch["chat_id"]; title = ch["title"] or cid
        if cid.startswith("@"):
            url = f"https://t.me/{cid.lstrip('@')}"
        else:
            url = f"https://t.me/c/{str(cid).replace('-100', '')}"
        buttons.append([InlineKeyboardButton(text=f"📢 {title}", url=url)])
    buttons.append([InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== КЛАВИАТУРЫ ==========
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="search"),
         InlineKeyboardButton(text="🔎 Быстрый поиск", callback_data="fast_search")],
        [InlineKeyboardButton(text="🆕 Новинки", callback_data="new"),
         InlineKeyboardButton(text="🍿 Жанры", callback_data="genres")],
        [InlineKeyboardButton(text="🌍 Страны", callback_data="countries"),
         InlineKeyboardButton(text="☀️ О проекте", callback_data="about")],
        [InlineKeyboardButton(text="🛒 Заказать фильм", callback_data="order_film"),
         InlineKeyboardButton(text="🛠 Тех. поддержка", callback_data="support")]
    ])

def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить фильм", callback_data="admin_add_film")],
        [InlineKeyboardButton(text="🗑 Удалить фильм", callback_data="admin_del_film")],
        [InlineKeyboardButton(text="📋 Список фильмов", callback_data="admin_list_films")],
        [InlineKeyboardButton(text="📢 Каналы подписки", callback_data="admin_channels")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

def back_kb(callback="main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=callback)]
    ])

# ========== ХЕЛПЕР: ОТПРАВИТЬ РАЗДЕЛ С КАРТИНКОЙ ==========
async def send_section(callback, image_url, caption, keyboard):
    """Отправляет раздел с картинкой (если есть) или только текстом."""
    if image_url:
        try:
            await callback.message.edit_media(
                media=types.InputMediaPhoto(media=image_url, caption=caption, parse_mode="HTML"),
                reply_markup=keyboard
            )
            return
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            try:
                await callback.message.answer_photo(photo=image_url, caption=caption, reply_markup=keyboard, parse_mode="HTML")
                return
            except Exception:
                pass
    # Если картинки нет — просто текст
    try:
        await callback.message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(caption, reply_markup=keyboard, parse_mode="HTML")

# ========== ФОРМАТИРОВАНИЕ ==========
def format_film(film):
    fid, title, desc, genre, country, year, quality, kp, imdb, poster, watch, category, _ = film
    text = (
        f"🎬 <b>Название: {title}</b>\n"
        f"⭐️ КП: {kp} | IMDb: {imdb}\n"
        f"🌍 Страна: {country}\n"
        f"💎 Качество: {quality}\n"
        f"📁 Категория: {category}\n"
        f"🎭 Жанр: {genre}\n"
        f"📅 Год: {year}\n"
    )
    if desc:
        text += f"\n📝 {desc[:300]}\n"
    return text

def film_kb(film_id, prefix="catalog", page=0):
    site_url = f"{SITE_URL}/film/{film_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😍 Смотреть онлайн", url=site_url)],
        [InlineKeyboardButton(text="🚀 Опубликовать в канал", callback_data=f"publish_{film_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{prefix}_page_{page}")]
    ])

# ========== ХЭНДЛЕРЫ ==========
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    ok, not_sub = await is_subscribed(message.from_user.id)
    if not ok:
        await message.answer(
            f"Салам, {message.from_user.first_name}! 👋\n\n"
            "Для использования бота подпишись на каналы:",
            reply_markup=subscribe_kb(not_sub)
        )
        return
    welcome = (
        f"Добро пожаловать, {message.from_user.first_name}! 👋\n\n"
        "🎬 <b>ZEDkino Bot</b> — каталог фильмов с удобным поиском."
    )
    try:
        await message.answer_photo(photo=IMG_MAIN, caption=welcome, reply_markup=main_menu_kb(), parse_mode="HTML")
    except Exception:
        await message.answer(welcome, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub(callback: types.CallbackQuery):
    ok, not_sub = await is_subscribed(callback.from_user.id)
    if ok:
        await callback.message.edit_text("✅ Подписка подтверждена! Напиши /start заново.")
    else:
        await callback.answer("Ты ещё не подписался 😞", show_alert=True)

@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    welcome = (
        f"Добро пожаловать, {callback.from_user.first_name}! 👋\n\n"
        "🎬 <b>ZEDkino Bot</b> — каталог фильмов с удобным поиском."
    )
    await send_section(callback, IMG_MAIN, welcome, main_menu_kb())

@dp.callback_query(lambda c: c.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()

@dp.callback_query(lambda c: c.data == "about")
async def about(callback: types.CallbackQuery):
    text = "☀️ <b>О проекте</b>\n\nZEDkino Bot — бесплатный каталог фильмов."
    await send_section(callback, IMG_ABOUT, text, back_kb())

@dp.callback_query(lambda c: c.data == "profile")
async def profile(callback: types.CallbackQuery):
    user = callback.from_user
    text = (
        f"👤 <b>Мой профиль</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📛 Имя: {user.full_name}\n"
        f"🔗 Username: @{user.username or '—'}"
    )
    await send_section(callback, IMG_PROFILE, text, back_kb())

@dp.callback_query(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    text = "🛠 <b>Тех. поддержка</b>\n\nПиши: @твой_юзернейм"
    await send_section(callback, IMG_SUPPORT, text, back_kb())

# ===== АДМИН =====
@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        await message.answer_photo(photo=IMG_ADMIN, caption="⚙️ <b>Панель управления</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")
    except Exception:
        await message.answer("⚙️ Панель управления", reply_markup=admin_menu_kb())

@dp.callback_query(lambda c: c.data == "admin_add_film")
async def admin_add_film(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    user_states[callback.from_user.id] = "admin_add_film"
    await callback.message.edit_text("➕ Напиши название фильма — найду в TMDB.", reply_markup=back_kb("admin_back"))

@dp.callback_query(lambda c: c.data == "admin_del_film")
async def admin_del_film(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    user_states[callback.from_user.id] = "admin_del_film"
    await callback.message.edit_text("🗑 Напиши ID фильма.", reply_markup=back_kb("admin_back"))

@dp.callback_query(lambda c: c.data == "admin_list_films")
async def admin_list_films(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    films = get_films(limit=100)
    if not films:
        await callback.message.edit_text("База пуста.", reply_markup=back_kb("admin_back")); return
    text = "📋 <b>Фильмы:</b>\n\n" + "\n".join([f"ID {f[0]} — {f[1]}" for f in films])
    await callback.message.edit_text(text[:4000], reply_markup=back_kb("admin_back"), parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "admin_channels")
async def admin_channels(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    channels = get_channels()
    text = "📢 <b>Каналы подписки</b>\n\n"
    if channels:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch['title'] or ch['chat_id']}\n   <code>{ch['chat_id']}</code>\n"
    else:
        text += "Список пуст.\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="admin_del_channel")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "admin_add_channel")
async def admin_add_channel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    user_states[callback.from_user.id] = "admin_add_channel"
    await callback.message.edit_text("Напиши @username или -100xxxx канала.", reply_markup=back_kb("admin_back"))

@dp.callback_query(lambda c: c.data == "admin_del_channel")
async def admin_del_channel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    user_states[callback.from_user.id] = "admin_del_channel"
    await callback.message.edit_text("Напиши @username канала для удаления.", reply_markup=back_kb("admin_back"))

@dp.callback_query(lambda c: c.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    try:
        await callback.message.edit_media(
            media=types.InputMediaPhoto(media=IMG_ADMIN, caption="⚙️ <b>Панель управления</b>", parse_mode="HTML"),
            reply_markup=admin_menu_kb()
        )
    except Exception:
        await callback.message.edit_text("⚙️ Панель управления", reply_markup=admin_menu_kb())

# ===== РАЗДЕЛЫ С КАРТИНКАМИ =====
@dp.callback_query(lambda c: c.data == "new")
async def show_new(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Фильмы", callback_data="new_cat_Фильмы")],
        [InlineKeyboardButton(text="📺 Сериалы", callback_data="new_cat_Сериалы")],
        [InlineKeyboardButton(text="🎨 Мультфильмы", callback_data="new_cat_Мультфильмы")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])
    await send_section(callback, IMG_NEW, "🆕 <b>Новинки</b>\n\nВыбери категорию:", kb)

@dp.callback_query(lambda c: c.data.startswith("new_cat_"))
async def show_new_category(callback: types.CallbackQuery):
    category = callback.data.replace("new_cat_", "")
    await show_films_page(callback, category=category, page=0, prefix="new")

@dp.callback_query(lambda c: c.data == "genres")
async def show_genres(callback: types.CallbackQuery):
    genres = get_genres()
    if not genres:
        await send_section(callback, IMG_GENRES, "Жанров пока нет.", back_kb()); return
    buttons = []; row = []
    for g in genres:
        row.append(InlineKeyboardButton(text=f"🍿 {g}", callback_data=f"genre_{g}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
    await send_section(callback, IMG_GENRES, "🍿 <b>Жанры</b>\n\nВыбери жанр:", InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(lambda c: c.data.startswith("genre_"))
async def show_genre_films(callback: types.CallbackQuery):
    genre = callback.data.replace("genre_", "")
    await show_films_page(callback, genre=genre, page=0, prefix="genre")

@dp.callback_query(lambda c: c.data == "countries")
async def show_countries(callback: types.CallbackQuery):
    countries = get_countries()
    if not countries:
        await send_section(callback, IMG_COUNTRIES, "Стран пока нет.", back_kb()); return
    buttons = []; row = []
    for cn in countries[:30]:
        row.append(InlineKeyboardButton(text=f"🌍 {cn}", callback_data=f"country_{cn}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
    await send_section(callback, IMG_COUNTRIES, "🌍 <b>Страны</b>\n\nВыбери страну:", InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(lambda c: c.data.startswith("country_"))
async def show_country_films(callback: types.CallbackQuery):
    country = callback.data.replace("country_", "")
    await show_films_page(callback, country=country, page=0, prefix="country")

# ===== СПИСОК ФИЛЬМОВ =====
async def show_films_page(callback, category=None, genre=None, country=None, page=0, prefix="catalog", query=None):
    limit = 10; offset = page * limit
    if query:
        films = search_films(query, limit, offset)
        total = len(search_films(query, 1000, 0))
    else:
        films = get_films(category=category, genre=genre, country=country, limit=limit, offset=offset)
        total = count_films(category=category, genre=genre, country=country)
    total_pages = max(1, (total + limit - 1) // limit)
    if not films:
        await callback.message.edit_text("😔 Ничего не найдено.", reply_markup=back_kb("main_menu")); return
    buttons = []
    for f in films:
        fid, title, *_ = f
        buttons.append([InlineKeyboardButton(text=f"🎬 {title}", callback_data=f"view_{fid}_{prefix}_{page}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}_page_{page+1}"))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    label = "📽 Каталог"
    if category: label = f"📁 {category}"
    if genre: label = f"🍿 {genre}"
    if country: label = f"🌍 {country}"
    await callback.message.edit_text(f"<b>{label}</b>\n\nНайдено: {total}\n\nВыбери фильм:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: re.match(r"^(new|genre|country|search)_page_\d+$", c.data or ""))
async def paginate(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    prefix = parts[0]; page = int(parts[-1])
    await show_films_page(callback, page=page, prefix=prefix)

# ===== КАРТОЧКА ФИЛЬМА =====
@dp.callback_query(lambda c: c.data.startswith("view_"))
async def view_film(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    film_id = int(parts[1])
    prefix = parts[2] if len(parts) > 2 else "catalog"
    page = int(parts[3]) if len(parts) > 3 else 0
    film = get_film(film_id)
    if not film:
        await callback.answer("Фильм не найден", show_alert=True); return
    text = format_film(film)
    poster_url = film[9]
    kb = film_kb(film_id, prefix, page)
    try:
        if poster_url:
            await callback.message.delete()
            await callback.message.answer_photo(photo=poster_url, caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# ===== ПОИСК =====
@dp.callback_query(lambda c: c.data == "search")
async def search_menu(callback: types.CallbackQuery):
    user_states[callback.from_user.id] = "search"
    await send_section(callback, IMG_SEARCH, "🔍 <b>Поиск по названию</b>\n\nНапиши название фильма.", back_kb())

@dp.callback_query(lambda c: c.data == "fast_search")
async def fast_search(callback: types.CallbackQuery):
    user_states[callback.from_user.id] = "search"
    await send_section(callback, IMG_SEARCH, "🔎 <b>Быстрый поиск</b>\n\nНапиши название.", back_kb())

# ===== ЗАКАЗ =====
@dp.callback_query(lambda c: c.data == "order_film")
async def order_film(callback: types.CallbackQuery):
    user_states[callback.from_user.id] = "order_film"
    await send_section(callback, IMG_ORDER, "🛒 <b>Заказать фильм</b>\n\nНапиши название.", back_kb())

# ===== ТЕКСТ =====
@dp.message()
async def handle_text(message: types.Message):
    if not message.text or message.text.startswith("/"): return
    user_id = message.from_user.id
    state = user_states.get(user_id)
    text = message.text.strip()

    if state == "admin_add_film" and user_id == ADMIN_ID:
        user_states[user_id] = None
        await message.answer(f"⏳ Ищу «{text}»...")
        info = await fetch_tmdb_info(text)
        if not info:
            await message.answer("❌ Не найдено."); return
        add_film(info["title"], info["description"], info["genre"], info["country"],
                 info["year"], "FHD (1080p)", info["rating"], info["rating"], info["poster_url"])
        await message.answer(f"✅ «{info['title']}» добавлен!")
        return

    if state == "admin_del_film" and user_id == ADMIN_ID:
        user_states[user_id] = None
        try:
            name = delete_film(int(text))
            await message.answer(f"✅ «{name}» удалён." if name else "❌ Не найден.")
        except ValueError:
            await message.answer("❌ ID должен быть числом.")
        return

    if state == "admin_add_channel" and user_id == ADMIN_ID:
        user_states[user_id] = None
        try:
            chat = await bot.get_chat(text)
            add_channel(text, chat.title or text)
            await message.answer(f"✅ Канал «{chat.title or text}» добавлен.")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)[:200]}")
        return

    if state == "admin_del_channel" and user_id == ADMIN_ID:
        user_states[user_id] = None
        remove_channel(text)
        await message.answer("✅ Канал удалён.")
        return

    if state == "order_film":
        user_states[user_id] = None
        await message.answer(f"⏳ Ищу «{text}»...")
        info = await fetch_tmdb_info(text)
        if not info:
            await message.answer("😔 Не найдено."); return
        add_film(info["title"], info["description"], info["genre"], info["country"],
                 info["year"], "FHD (1080p)", info["rating"], info["rating"], info["poster_url"])
        await message.answer(f"✅ «{info['title']}» добавлен в каталог!")
        return

    if state == "search" or not state:
        user_states[user_id] = None
        films = search_films(text, limit=10)
        if not films:
            await message.answer(f"😔 По запросу «{text}» ничего не найдено."); return
        buttons = []
        for f in films:
            buttons.append([InlineKeyboardButton(text=f"🎬 {f[1]}", callback_data=f"view_{f[0]}_search_0")])
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
        await message.answer(f"🔍 Найдено: {len(films)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

# ===== КОМАНДЫ =====
@dp.message(Command("addfilm"))
async def add_film_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.replace("/addfilm", "").strip()
    if not args: await message.answer("Напиши: /addfilm Название"); return
    await message.answer(f"⏳ Ищу «{args}»...")
    info = await fetch_tmdb_info(args)
    if not info: await message.answer("❌ Не найдено."); return
    add_film(info["title"], info["description"], info["genre"], info["country"],
             info["year"], "FHD (1080p)", info["rating"], info["rating"], info["poster_url"])
    await message.answer(f"✅ «{info['title']}» добавлен!")

@dp.message(Command("delfilm"))
async def del_film_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.replace("/delfilm", "").strip()
    if not args: await message.answer("Напиши: /delfilm ID"); return
    try:
        name = delete_film(int(args))
        await message.answer(f"✅ «{name}» удалён." if name else "❌ Не найден.")
    except ValueError:
        await message.answer("❌ ID должен быть числом.")

@dp.message(Command("listfilms"))
async def list_films_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    films = get_films(limit=100)
    if not films: await message.answer("База пуста."); return
    text = "📋 Фильмы:\n\n" + "\n".join([f"ID {f[0]} — {f[1]}" for f in films])
    await message.answer(text[:4000])

# ===== ЗАПУСК =====
async def main():
    init_db()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
