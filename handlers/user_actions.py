from io import BytesIO

from aiogram import Dispatcher, types
from aiogram.types.message import ContentType
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.deep_linking import get_start_link, decode_payload

from handlers.consts import GET_USER_TASKS, WITHDRAWAL, WELCOME_MESSAGE, WALLET_MESSAGE, DISCORD_MESSAGE
from handlers.api import get_user, get_tasks, register_task, send_proof_request, send_withdrawal_request, update_user

from handlers.helpers import remove_p_tag, wallet_valid, discord_valid


class UserAction(StatesGroup):
    user_start = State()

    waiting_wallet = State()

    waiting_discord = State()

    select_action = State()

    withdrawal_create = State()

    get_user_tasks = State()

    select_task = State()

    send_answer = State()


async def user_start(message: types.Message, state: FSMContext):
    affiliate = None
    args = message.get_args()
    if args:
        affiliate = decode_payload(args)
    user = get_user(user_id=message.from_user.id, tg_username=message.from_user.username, affiliate=affiliate)

    if not user.get('welcome_passed'):
        await message.answer(WALLET_MESSAGE)
        await state.set_state(UserAction.waiting_wallet.state)

    else:
        actions = [GET_USER_TASKS, WITHDRAWAL]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

        for action in actions:
            keyboard.add(action)

        await message.answer(
            "Select your next action: \n your ref link is {}".format(await get_start_link(message.from_user.id, encode=True)),
            reply_markup=keyboard,
        )
        await state.set_state(UserAction.user_start.state)


async def wallet_address_entered(message: types.Message, state: FSMContext):
    wallet_id = message.text
    if not wallet_valid(wallet_id):
        await message.answer("Please send me right wallet.")
        return
    await message.answer(DISCORD_MESSAGE)
    await state.update_data(wallet=wallet_id)
    await state.set_state(UserAction.waiting_discord.state)


async def discord_username_entered(message: types.Message, state: FSMContext):
    discord_username = message.text
    if not wallet_valid(discord_username):
        await message.answer("Please send me right discord username.")
        return

    user_data = await state.get_data()
    user_updated = update_user(message.from_user.id, user_data.get('wallet'), discord_username)

    msg_text = 'You profile is updated'
    if not user_updated:
        msg_text = 'Something went wrong'

    await message.answer(msg_text, parse_mode='HTML')
    await state.finish()


async def select_action(message: types.Message, state: FSMContext):
    action = message.text.lower()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if action == GET_USER_TASKS:
        tasks = get_tasks(message.from_user.id)
        await state.update_data(tasks=tasks)
        for task in tasks:
            keyboard.add(str(task['name']))

        await message.answer("Select task:", reply_markup=keyboard)
        await state.set_state(UserAction.get_user_tasks.state)

    elif action == WITHDRAWAL:
        await message.answer("Input withdrawal amount:")
        await state.set_state(UserAction.withdrawal_create.state)


async def create_withdrawal(message: types.Message, state: FSMContext):
    withdrawal_amount = message.text.lower()
    created = send_withdrawal_request(message.from_user.id, withdrawal_amount)
    msg_text = 'You withdrawal is created'
    if not created:
        msg_text = 'Something went wrong'

    await message.answer(msg_text, parse_mode='HTML')
    await state.finish()


async def select_task(message: types.Message, state: FSMContext):
    task_name = message.text
    user_data = await state.get_data()
    for task in user_data.get('tasks'):
        if str(task['name']) == task_name:
            task_desc = remove_p_tag(task['description'])
            register_task(message.from_user.id, task['id'])
            await message.answer(task_desc, parse_mode='HTML')
            await state.update_data(user_task=task)
            await state.set_state(UserAction.select_task.state)


async def send_proof(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    task = state_data.get('user_task')
    proof_type = task.get('proof_type')
    task_id = task.get('id')

    if proof_type == 'text':
        proof_created = send_proof_request(
            user_id=message.from_user.id,
            task_id=task_id,
            text_proof=message.text
        )
    else:
        data = BytesIO()
        raw = await message.photo[0].download(destination=data)
        proof_created = send_proof_request(
            user_id=message.from_user.id,
            task_id=task_id,
            image_proof=data
        )
    msg_text = 'You proof is accepted'
    if not proof_created:
        msg_text = 'Something went wrong'

    await message.answer(msg_text, parse_mode='HTML')
    await state.finish()


def register_handlers_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands="start", state="*")

    dp.register_message_handler(wallet_address_entered, state=UserAction.waiting_wallet)
    dp.register_message_handler(discord_username_entered, state=UserAction.waiting_discord)

    dp.register_message_handler(select_action, state=UserAction.user_start)
    dp.register_message_handler(create_withdrawal, state=UserAction.withdrawal_create)
    dp.register_message_handler(select_task, state=UserAction.get_user_tasks)
    dp.register_message_handler(
        send_proof, state=UserAction.select_task, content_types=[ContentType.TEXT, ContentType.PHOTO]
    )
