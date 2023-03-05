from io import BytesIO
from decimal import Decimal

from aiogram import Dispatcher, types
from aiogram.types.message import ContentType
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.deep_linking import get_start_link, decode_payload

from handlers.consts import GET_USER_TASKS, WITHDRAWAL, WELCOME_MESSAGE, WALLET_MESSAGE, DISCORD_MESSAGE, \
    MAIN_MENU_MESSAGE, CHANGE_WALLET_ADDRESS
from handlers.api import get_user, get_tasks, register_task, send_proof_request, send_withdrawal_request, update_user

from handlers.helpers import wallet_valid, discord_valid, amount_valid, remove_tags


async def add_menu_button():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Menu")
    return keyboard


class UserAction(StatesGroup):
    user_start = State()

    waiting_wallet = State()

    waiting_discord = State()

    new_wallet_address = State()

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
        await message.answer(WELCOME_MESSAGE)
        await message.answer(WALLET_MESSAGE)
        await state.set_state(UserAction.waiting_wallet.state)

    else:
        actions = [GET_USER_TASKS, CHANGE_WALLET_ADDRESS, WITHDRAWAL]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

        for action in actions:
            keyboard.add(action)

        await message.answer(
            MAIN_MENU_MESSAGE.format(
                message.from_user.first_name,
                Decimal(user.get('unverified_balance')) + Decimal(user.get('balance')),
                user.get('balance'),
                user.get('referrals'),
                await get_start_link(message.from_user.id, encode=True)
            ),
            reply_markup=keyboard,
        )
        await state.set_state(UserAction.user_start.state)


async def wallet_address_entered(message: types.Message, state: FSMContext):
    wallet_id = message.text
    if not wallet_valid(wallet_id):
        await message.answer("Please send me correct wallet.")
        return
    await message.answer(DISCORD_MESSAGE)
    await state.update_data(wallet=wallet_id)
    await state.set_state(UserAction.waiting_discord.state)


async def discord_username_entered(message: types.Message, state: FSMContext):
    discord_username = message.text
    if not discord_valid(discord_username):
        await message.answer("Please send me correct discord username.")
        return

    user_data = await state.get_data()
    user_updated = update_user(message.from_user.id, user_data.get('wallet'), discord_username)

    msg_text = 'You profile is updated'
    if not user_updated:
        msg_text = 'Something went wrong'
    kb = await add_menu_button()
    await message.answer(msg_text, parse_mode='HTML', reply_markup=kb)


async def select_action(message: types.Message, state: FSMContext):
    action = message.text.lower()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if action == GET_USER_TASKS.lower():
        tasks = get_tasks(message.from_user.id)
        await state.update_data(tasks=tasks)
        for task in tasks:
            keyboard.add(str(task['name']))

        await message.answer("Select task:", reply_markup=keyboard)
        await state.set_state(UserAction.get_user_tasks.state)

    elif action == WITHDRAWAL.lower():
        await message.answer("Input withdrawal amount:")
        await state.set_state(UserAction.withdrawal_create.state)

    elif action == CHANGE_WALLET_ADDRESS.lower():
        await message.answer("Input your new wallet address:")
        await state.set_state(UserAction.new_wallet_address.state)


async def new_wallet_address_entered(message: types.Message, state: FSMContext):
    wallet_id = message.text
    if not wallet_valid(wallet_id):
        await message.answer("Please send me correct wallet.")
        return
    updated = update_user(user_id=message.from_user.id, wallet_id=wallet_id)
    msg_text = 'You wallet is updated'
    if not updated:
        msg_text = 'Something went wrong'
    kb = await add_menu_button()
    await message.answer(msg_text, parse_mode='HTML', reply_markup=kb)
    await state.finish()


async def create_withdrawal(message: types.Message, state: FSMContext):
    withdrawal_amount = message.text.lower()
    if not amount_valid(withdrawal_amount):
        kb = await add_menu_button()
        await message.answer("Please send me correct withdrawal amount.", reply_markup=kb)
        return

    created = send_withdrawal_request(message.from_user.id, withdrawal_amount)
    msg_text = 'You withdrawal is created'
    if not created:
        msg_text = 'Something went wrong'

    kb = await add_menu_button()
    await message.answer(msg_text, parse_mode='HTML', reply_markup=kb)
    await state.finish()


async def select_task(message: types.Message, state: FSMContext):
    task_name = message.text
    user_data = await state.get_data()
    for task in user_data.get('tasks'):
        if str(task['name']) == task_name:
            task_desc = remove_tags(task['description'])
            register_task(message.from_user.id, task['id'])

            await message.answer(task_desc, parse_mode='html')
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
        if len(message.photo) == 0:
            kb = await add_menu_button()
            await message.answer("Please send me some image.", reply_markup=kb)
            return

        data = BytesIO()
        raw = await message.photo[0].download(destination=data)
        proof_created = send_proof_request(
            user_id=message.from_user.id,
            task_id=task_id,
            image_proof=data
        )
    msg_text = task.get('success_text') if task.get('need_validation') else 'Your proof is accepted'
    if not proof_created:
        msg_text = task.get('fail_text')
    kb = await add_menu_button()
    await message.answer(msg_text, parse_mode='HTML', reply_markup=kb)
    await state.finish()


def register_handlers_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands="start", state="*")
    dp.register_message_handler(user_start, Text(equals="menu", ignore_case=True), state="*")

    dp.register_message_handler(wallet_address_entered, state=UserAction.waiting_wallet)
    dp.register_message_handler(discord_username_entered, state=UserAction.waiting_discord)

    dp.register_message_handler(select_action, state=UserAction.user_start)
    dp.register_message_handler(new_wallet_address_entered, state=UserAction.new_wallet_address)
    dp.register_message_handler(create_withdrawal, state=UserAction.withdrawal_create)
    dp.register_message_handler(select_task, state=UserAction.get_user_tasks)
    dp.register_message_handler(
        send_proof, state=UserAction.select_task, content_types=[ContentType.TEXT, ContentType.PHOTO]
    )
