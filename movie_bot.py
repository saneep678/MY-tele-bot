import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Shorthand to Full Name mappings for Print
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

def get_movie_poster_url(title: str):
    """Fetches a movie poster URL from TMDb API based on the title."""
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title
    }
    
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data['results']:
            return None, "Movie not found on TMDb."
            
        movie = data['results'][0]
        poster_path = movie.get('poster_path')
        if not poster_path:
            return None, "Poster not available for this movie."

        base_url = "https://image.tmdb.org/t/p/original"
        poster_url = f"{base_url}{poster_path}"
        
        return poster_url, None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None, "Failed to connect to the movie database."

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles a text message, extracts all details, fetches the poster, and sends a single post.
    """
    message_text = update.effective_message.text.strip()
    
    if message_text.startswith('/'):
        return

    lines = message_text.split('\n')

    if len(lines) != 4:
        await update.message.reply_text(
            "The message format is incorrect. It should have exactly four lines."
        )
        return
    
    # Extract the parts from the message
    movie_title = lines[0].strip()
    print_shorthand = lines[1].strip().lower()
    language_shorthand = lines[2].strip().lower()
    download_link = lines[3].strip()

    # Get movie poster URL from TMDb
    await update.message.reply_text("Searching for poster...")
    poster_url, error_message = get_movie_poster_url(movie_title)

    if error_message:
        await update.message.reply_text(error_message)
        return

    # Map the shorthand codes to full names
    try:
        print_full = print_map.get(print_shorthand, "Unknown")
        if print_full == "Unknown":
             await update.message.reply_text(
                "An error occurred. Make sure your print shorthand is correct."
            )
             return
    except KeyError:
        await update.message.reply_text(
            "An error occurred. Make sure your print shorthand is correct."
        )
        return

    try:
        language_parts = language_shorthand.split(',')
        language_full = ', '.join([language_map[l] for l in language_parts])
    except KeyError:
        await update.message.reply_text(
            "An error occurred. Make sure your language shorthand is correct."
        )
        return
        
    # Construct the final formatted post text, with a hardcoded quality line
    final_post = (
        f"🎬 **{movie_title}**\n\n"
        f"🖨️ Print: {print_full}\n"
        f"🎞️ Quality: 360p,480p,720p,1080p\n"
        f"🗣️ Language: {language_full}\n\n"
        "❌ No Ads | ✅ Clean Download | 📥 Direct Link Below\n\n"
        "✨ #CinemaReddy"
    )

    # Create the inline button and keyboard markup
    button = InlineKeyboardButton("🔗 Download Now", url=download_link)
    keyboard = InlineKeyboardMarkup([[button]])

    # Send the final post with the fetched poster and all details
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=poster_url,
        caption=final_post,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    application.run_polling()

if __name__ == "__main__":

    main()
