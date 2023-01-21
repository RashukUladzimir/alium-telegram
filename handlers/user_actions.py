from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.deep_linking import get_start_link, decode_payload

from handlers.consts import GET_USER_TASKS, WITHDRAWAL
from handlers.api import get_user, get_tasks, register_task, send_proof_request, send_withdrawal_request

from handlers.helpers import remove_p_tag


class UserAction(StatesGroup):
    user_start = State()

    welcome_tasks = State()

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
        await message.answer('Please send your discord username')
        await state.set_state(UserAction.welcome_tasks.state)

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
    if not created:
        await message.answer('Something went wrong', parse_mode='HTML')
        await state.finish()
    else:
        await message.answer('You withdrawal is created', parse_mode='HTML')
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
        proof_created = send_proof_request(
            user_id=message.from_user.id,
            task_id=task_id,
            text_proof=message.photo[-1]
        )
    if not proof_created:
        await message.answer('Something went wrong', parse_mode='HTML')
        await state.finish()
    else:
        await message.answer('You proof is accepted', parse_mode='HTML')
        await state.finish()


def register_handlers_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands="start", state="*")
    dp.register_message_handler(select_action, state=UserAction.user_start)
    dp.register_message_handler(create_withdrawal, state=UserAction.withdrawal_create)
    dp.register_message_handler(select_task, state=UserAction.get_user_tasks)
    dp.register_message_handler(send_proof, state=UserAction.select_task)
