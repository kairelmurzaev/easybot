import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, CallbackContext, filters
import aiohttp
from aiohttp import web
from io import BytesIO
from datetime import datetime
import os

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# States
CHOOSING, DRIVER_NAME, CLIENT_NAME, CAR_MODEL, PLATE_NUMBER, ODOMETER, PETROL_LEVEL, MONEY_PAID, DELIVERY_ADDRESS, PROBLEMS, PICTURE = range(11)

# Define a function to handle the /start command
async def start(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("Delivery"), KeyboardButton("Pickup")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text('Please choose an option:', reply_markup=reply_markup)
    return CHOOSING

# Define a function to handle initial button clicks
async def initial_choice(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if text in ["Delivery", "Pickup"]:
        context.user_data['choice'] = text
        await update.message.reply_text('Please provide the driver\'s name:')
        return DRIVER_NAME
    else:
        await update.message.reply_text('Please choose either "Delivery" or "Pickup".')
        return CHOOSING

# Define a function to handle the user's response for each question
async def process_driver_name(update: Update, context: CallbackContext) -> int:
    context.user_data['driver_name'] = update.message.text
    await update.message.reply_text('Please provide the client\'s name:')
    return CLIENT_NAME

async def process_client_name(update: Update, context: CallbackContext) -> int:
    context.user_data['client_name'] = update.message.text
    await update.message.reply_text('Please provide the car model:')
    return CAR_MODEL

async def process_car_model(update: Update, context: CallbackContext) -> int:
    context.user_data['car_model'] = update.message.text
    await update.message.reply_text('Please provide the plate number:')
    return PLATE_NUMBER

async def process_plate_number(update: Update, context: CallbackContext) -> int:
    context.user_data['plate_number'] = update.message.text
    await update.message.reply_text('Please provide the car odometer:')
    return ODOMETER

async def process_odometer(update: Update, context: CallbackContext) -> int:
    context.user_data['odometer'] = update.message.text
    await update.message.reply_text('Please provide the petrol level:')
    return PETROL_LEVEL

async def process_petrol_level(update: Update, context: CallbackContext) -> int:
    context.user_data['petrol_level'] = update.message.text
    await update.message.reply_text('Please provide the money paid:')
    return MONEY_PAID

async def process_money_paid(update: Update, context: CallbackContext) -> int:
    context.user_data['money_paid'] = update.message.text
    await update.message.reply_text('Please provide the delivery address:')
    return DELIVERY_ADDRESS

async def process_delivery_address(update: Update, context: CallbackContext) -> int:
    context.user_data['delivery_address'] = update.message.text
    await update.message.reply_text('Any problems with the car?')
    return PROBLEMS

async def process_problems(update: Update, context: CallbackContext) -> int:
    context.user_data['problems'] = update.message.text
    await update.message.reply_text('Please take a picture of the car:')
    return PICTURE

# Function to download the photo content as a BytesIO object
async def download_photo(file_path: str) -> BytesIO:
    """Download photo content as a BytesIO object."""
    async with aiohttp.ClientSession() as session:
        async with session.get(file_path) as response:
            if response.status == 200:
                return BytesIO(await response.read())
            else:
                raise ValueError(f"Failed to download photo: {response.status}")

# Function to handle photos
async def reg_photo(photo, context):
    photo_file = await context.bot.get_file(photo.file_id)
    photo_content = await download_photo(photo_file.file_path)
    return InputMediaPhoto(media=photo_content)

# Function to handle the user's response for photos
async def picture_response(update: Update, context: CallbackContext) -> int:
    if update.message.photo:
        # Process the highest resolution photo
        highest_res_photo = update.message.photo[-1]
        media_photo = await reg_photo(highest_res_photo, context)
        context.user_data.setdefault('photos', []).append(media_photo)
        logger.info(f"Total photos received: {len(context.user_data['photos'])}")

    # Add a "Done" button to allow the user to submit the form
    keyboard = [
        [KeyboardButton("Done")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text('.', reply_markup=reply_markup)
    return PICTURE

# Define a function to end the photo collection and send the data
async def done(update: Update, context: CallbackContext) -> int:
    logger.info("Done function called")

    text = update.message.text
    logger.info(f"Received message text: {text}")
    if text == "Done":
        logger.info("Message text is 'Done'")
        # Check if all questions have been answered
        required_fields = ['driver_name', 'client_name', 'car_model', 'plate_number', 'odometer', 'petrol_level', 'money_paid', 'delivery_address', 'problems']
        if all(field in context.user_data for field in required_fields):
            # Prepare form data with current date and time
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            form_data = [
                f"Date and Time: {current_time}",
                f"Driver's Name: {context.user_data['driver_name']}",
                f"Client's Name: {context.user_data['client_name']}",
                f"Car Model: {context.user_data['car_model']}",
                f"Plate Number: {context.user_data['plate_number']}",
                f"Odometer: {context.user_data['odometer']}",
                f"Petrol Level: {context.user_data['petrol_level']}",
                f"Money Paid: {context.user_data['money_paid']}",
                f"Delivery Address: {context.user_data['delivery_address']}",
                f"Problems: {context.user_data['problems']}"
            ]

            # Concatenate all the answers into one message
            form_message = "\n".join(form_data)

            # Send form data to the appropriate group chat
            group_chat_id = ''
            if context.user_data['choice'] == 'Delivery':
                group_chat_id = '-1002057568399'  # Replace with the correct group chat ID for delivery
            else:  # Pickup
                group_chat_id = '-1002184262143'  # Replace with the correct group chat ID for pickup
            await context.bot.send_message(chat_id=group_chat_id, text=form_message)

            # Send all photos separately
            if 'photos' in context.user_data and context.user_data['photos']:
                for media_photo in context.user_data['photos']:
                    await context.bot.send_photo(chat_id=group_chat_id, photo=media_photo.media)

            await update.message.reply_text("Thank you! Your form has been submitted.")
            context.user_data.clear()
            return ConversationHandler.END
        else:
            await update.message.reply_text('Please complete all required fields.')
            return CHOOSING
    else:
        logger.info("Message text is not 'Done'")
        return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    update.message.reply_text('Conversation canceled. /start again to begin.')
    context.user_data.clear()
    return ConversationHandler.END

# Replace the DoneFilter class definition with this
class DoneFilter(filters.UpdateFilter):
    def filter(self, update: Update) -> bool:
        return (isinstance(update, Update) and
                update.message.text == "Done")

# Function to handle health checks
async def handle_health_check(request):
    return web.Response(text="Bot is running")

def main():
    # Your bot token
    TOKEN = os.getenv("TOKEN")

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler with the states CHOOSING, DRIVER_NAME, CLIENT_NAME, CAR_MODEL, PLATE_NUMBER, ODOMETER, PETROL_LEVEL, MONEY_PAID, DELIVERY_ADDRESS, PROBLEMS, PICTURE
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, initial_choice)],
            DRIVER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_driver_name)],
            CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_client_name)],
            CAR_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_car_model)],
            PLATE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_plate_number)],
            ODOMETER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_odometer)],
            PETROL_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_petrol_level)],
            MONEY_PAID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_money_paid)],
            DELIVERY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_delivery_address)],
            PROBLEMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_problems)],
            PICTURE: [MessageHandler(filters.PHOTO & ~filters.COMMAND, picture_response)],
        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(DoneFilter(), done)],
    )
    application.add_handler(conv_handler)

    # Add health check endpoint
    app = web.Application()
    app.add_routes([web.get('/health', handle_health_check)])

    # Start the web server for health checks
    port = int(os.environ.get("PORT", 8000))
    web.run_app(app, port=port)

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
