import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctimes) - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Environment variables for API keys
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Dictionary to store search results temporarily for each user
user_searches = {}

# Shorthand to Full Name mappings
print_map = {
    'd': 'DVD',
    'h': 'HD',
    'f': 'FHD',
}

language_map = {
    'h': 'Hindi',
    't': 'Telugu',
    'k': 'Kannada',
    'm': 'Malayalam',
    'e': 'English',
    'b': 'Bengali',
    'tm': 'Tamil',
}

def get_movie_search_results(title: str):
    """Fetches a list of movie search results from TMDb API."""
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title
    }
    
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Return a list of up to 5 results
        return data.get('results', [])[:5], None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None, "Failed to connect to the movie database."

def get_full_movie_details(movie_id: int):
    """Fetches full movie details including genres from TMDb API."""
    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {"api_key": TMDB_API_KEY}
    
    try:
        response = requests.get(movie_url, params=params)
        response.raise_for_status()
        movie = response.json()
        
        details = {
            "title": movie.get('title'),
            "poster_path": movie.get('poster_path'),
            "genres": [g['name'] for g in movie.get('genres', [])]
        }
        return details, None
    
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None, "Failed to get full movie details."

async def send_final_post(update: Update, context: ContextTypes.DEFAULT_TYPE, details: dict, parsed_data: dict) -> None:
    """Helper function to send the final, formatted post."""
    
    poster_path = details.get('poster_path')
    if not poster_path:
        await update.message.reply_text("Poster not available for this movie.")
        return

    base_url = "https://image.tmdb.org/t/p/original"
    poster_url = f"{base_url}{poster_path}"

    genres_string = ", ".join(details.get('genres', []))
    
    final_post = (
        f"🎬 **{details['title']}**\n\n"
        f"🖨️ Print: {parsed_data['print_full']}\n"
        f"🎞️ Quality: 360p,480p,720p,1080p\n"
        f"🗣️ Language: {parsed_data['language_full']}\n\n"
        f"**Genre:** {genres_string}\n\n"
        "❌ No Ads | ✅ Clean Download | 📥 Direct Link Below\n\n"
        "✨ #CinemaReddy"
    )

    button = InlineKeyboardButton("🔗 Download Now", url=parsed_data['link'])
    keyboard = InlineKeyboardMarkup([[button]])

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=poster_url,
        caption=final_post,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
async def handle_initial_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the initial four-line message and presents choices if needed."""
    user_id = update.effective_user.id
    message_text = update.effective_message.text.strip()
    
    if message_text.startswith('/'):
        return

    lines = message_text.split('\n')
    if len(lines) != 4:
        await update.message.reply_text("The message format is incorrect. It should have exactly four lines.")
        return
    
    movie_title = lines[0].strip()
    
    # Store other parsed data to be used later
    parsed_data = {
        'print_shorthand': lines[1].strip().lower(),
        'language_shorthand': lines[2].strip().lower(),
        'link': lines[3].strip(),
    }
    context.user_data['parsed_data'] = parsed_data

    await update.message.reply_text("Searching for movie...")
    search_results, error_message = get_movie_search_results(movie_title)

    if error_message:
        await update.message.reply_text(error_message)
        return

    if not search_results:
        await update.message.reply_text("Movie not found.")
        return
        
    if len(search_results) > 1:
        response_text = "I found multiple matches. Please reply with the number of the movie you want:\n\n"
        for i, movie in enumerate(search_results):
            year = movie.get('release_date', '')[:4]
            response_text += f"**{i+1}.** {movie['title']} ({year})\n"
        
        await update.message.reply_text(response_text)
        
        context.user_data['search_results'] = search_results
    else:
        # Only one result, so we get the full details and send the post
        selected_movie_id = search_results[0]['id']
        movie_details, error_message = get_full_movie_details(selected_movie_id)
        if error_message:
            await update.message.reply_text(error_message)
            return

        # Map the shorthand codes
        parsed_data['print_full'] = print_map.get(parsed_data['print_shorthand'], "Unknown")
        parsed_data['language_full'] = ', '.join([language_map[l] for l in parsed_data['language_shorthand'].split(',')])

        await send_final_post(update, context, movie_details, parsed_data)
        
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's choice from the list of movies."""
    user_choice = int(update.effective_message.text.strip()) - 1
    
    search_results = context.user_data.get('search_results')
    parsed_data = context.user_data.get('parsed_data')
    
    if not search_results or user_choice < 0 or user_choice >= len(search_results):
        await update.message.reply_text("Invalid choice. Please send a number from the list.")
        return
        
    selected_movie_id = search_results[user_choice]['id']
    
    await update.message.reply_text("Getting details for your chosen movie...")

    movie_details, error_message = get_full_movie_details(selected_movie_id)
    if error_message:
        await update.message.reply_text(error_message)
        return

    # Map the shorthand codes
    parsed_data['print_full'] = print_map.get(parsed_data['print_shorthand'], "Unknown")
    parsed_data['language_full'] = ', '.join([language_map[l] for l in parsed_data['language_shorthand'].split(',')])
    
    await send_final_post(update, context, movie_details, parsed_data)

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()
    
    # Handler for the initial four-line message
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_initial_message))
    
    # Handler for the user's numbered choice
    application.add_handler(MessageHandler(filters.Regex(r'^[1-9]$'), handle_choice))
    
    application.run_polling()

if __name__ == "__main__":
    if not TOKEN or not TMDB_API_KEY:
        raise ValueError("Please set the TELEGRAM_BOT_TOKEN and TMDB_API_KEY environment variables.")
    main()

if __name__ == "__main__":

    main()

