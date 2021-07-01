import requests
from pony.orm import db_session
from models import UserStates, UsersData
from settings import TOKEN, MY_GROUP_ID
import settings
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import random
import logging
import handlers

bot_logger = logging.getLogger('bot_log')


def config_loggers():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    stream_handler.setLevel(logging.INFO)
    bot_logger.addHandler(stream_handler)

    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M'))
    file_handler.setLevel(logging.DEBUG)
    bot_logger.addHandler(file_handler)

    bot_logger.setLevel(logging.DEBUG)


class Bot:
    """

    Echo bot for vk.com
    Use Python 3.7
    """

    def __init__(self, group_id, token):
        """

        :param group_id: ID группы vk
        :param token: Персональный секретный токен
        """
        self.group_id = group_id
        self.token = token
        self.vk = vk_api.VkApi(token=token)
        self.long_poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()

    def run(self):
        """

        Запуск бота
        """
        for event in self.long_poller.listen():
            # bot_logger.info(f'Got event {event.type}')
            try:
                self.got_event(event=event)
            except Exception:
                bot_logger.exception(f'Unexpected error')

    @db_session
    def got_event(self, event):
        """

        Отправка текстового сообщения пользователю, если получено новое
        :param event: VkBotMessageEvent object
        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            bot_logger.debug(f'Cannot handle this type of event {event.type}')
            return
        user_id = event.object.peer_id
        text = event.object.text
        state = UserStates.get(user_id=str(user_id))
        if text == '/help' and state is not None:
            state.delete()
            self.send_text(text_to_send=settings.HELP, user_id=user_id)
        elif text == '/ticket' and state is not None:
            state.delete()
            self.start_scenario(scenario_name='get_ticket', user_id=user_id)
        else:
            if state is not None:
                self.continue_scenario(user_id=user_id, text=text, state=state)
            else:
                for intent in settings.INTENTS:
                    bot_logger.debug(f'User gets {intent}')
                    if text in intent['tokens']:
                        if intent['answer']:
                            self.send_text(text_to_send=settings.HELP, user_id=user_id)
                        else:
                            self.start_scenario(scenario_name=intent['scenario'], user_id=user_id)
                        break
                else:
                    self.send_text(text_to_send=settings.HELP, user_id=user_id)

    def send_text(self, text_to_send, user_id):
        """

        Отправка текстового сообщения пользователю
        :param text_to_send: Текст для отправки
        :param user_id: Идентификатор пользователя (id пользователя вк)
        """
        self.api.messages.send(
            message=text_to_send,
            random_id=random.randint(0, 2 ** 30),
            peer_id=user_id
        )

    def send_ticket(self, image, user_id):
        """

        Отправка пользователю изображения билета с данными о заказе
        :param image: Изображение билета (в байтовом представлении)
        :param user_id: Идентификатор пользователя (id пользователя вк)
        """
        upload_url = self.api.photos.getMessagesUploadServer()['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.jpg', image, 'image/jpeg')}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)
        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'
        self.api.messages.send(
            attachment=attachment,
            random_id=random.randint(0, 2 ** 30),
            peer_id=user_id
        )

    def start_scenario(self, scenario_name, user_id):
        """

        Начало нового сценария
        :param scenario_name: Имя сценария
        :param user_id: Идентификатор пользователя (id пользователя вк)
        :return: Текст сообщения для отправки пользователю
        """
        scenario = settings.SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        self.send_text(text_to_send=step['text'], user_id=user_id)
        UserStates(user_id=str(user_id), scenario_name=scenario_name, step_name=first_step, context={})

    def continue_scenario(self, user_id, text, state):
        """

        Продолжение текущего сценария
        :param user_id: Идентификатор пользователя (id пользователя вк)
        :param text: Текст сообщения, полученный от пользователя
        :param state: Текущее состояние пользователя
        :return: Текст сообщения для отправки пользователю
        """
        steps = settings.SCENARIOS[state.scenario_name]['steps']
        step = steps[state.step_name]
        handler = getattr(handlers, step['handler'])
        if handler(text=text, context=state.context):
            self.on_handler(steps=steps, step=step, state=state, user_id=user_id, text=text)
        else:
            self.on_failure(step=step, user_id=user_id, state=state)

    def on_handler(self, steps, step, state, user_id, text):
        """

        Действие при успешном выполнении хэндлера
        :param steps: Доступные шаги
        :param step: Текущий шаг пользователя
        :param state: Текущее состояние пользователя
        :param user_id: Идентификатор пользователя (id пользователя вк)
        :param text: Текст сообщения, полученный от пользователя
        """
        next_step = steps[step['next_step']]
        text_to_send = next_step['text'].format(**state.context)
        self.send_text(text_to_send=text_to_send, user_id=user_id)
        if next_step['next_step']:
            state.step_name = step['next_step']
            if step['next_step'] == 'step_4':
                handlers.controller(
                    flights=settings.FLIGHTS,
                    city_departure=state.context['name_departure'],
                    city_arrival=state.context['name_arrival'],
                    date=state.context['date'],
                    context=state.context
                )
                self.send_flights(flights=state.context['flights'], user_id=user_id)
            elif step['next_step'] == 'step_7':
                self.send_data(user_id=user_id, state=state)
        else:
            image_handler = getattr(handlers, next_step['image'])
            image = image_handler(text=text, context=state.context)
            self.send_ticket(image=image, user_id=user_id)
            UsersData(
                departure=state.context['name_departure'],
                arrival=state.context['name_arrival'],
                date=state.context['user_flight'],
                sits=state.context['passengers'],
                comment=state.context['comment']
            )
            state.delete()

    def on_failure(self, step, user_id, state):
        """

        Действие при ошибке
        :param step: Текущий шаг пользователя
        :param user_id: Идентификатор пользователя (id пользователя вк)
        :param state: Текущее состояние пользователя
        """
        if 'таком' in step['failure_text']:
            self.send_departures(user_id=user_id)
            text_to_send = step['failure_text'].format(**state.context)
            self.send_text(text_to_send=text_to_send, user_id=user_id)
        elif 'данный' in step['failure_text']:
            self.send_arrivals(user_id=user_id, state=state)
            text_to_send = step['failure_text'].format(**state.context)
            self.send_text(text_to_send=text_to_send, user_id=user_id)
        elif state.context['data_error'] is not None:
            text_to_send = state.context['data_error'].format(**state.context)
            self.send_text(text_to_send=text_to_send, user_id=user_id)
            state.delete()
        else:
            text_to_send = step['failure_text'].format(**state.context)
            self.send_text(text_to_send=text_to_send, user_id=user_id)

    def send_flights(self, flights, user_id):
        """

        Отправка пользователю сообщений с доступными рейсами
        :param flights: Список доступных рейсов
        :param user_id: Идентификатор пользователя (id пользователя вк)
        """
        for flight in flights:
            self.api.messages.send(
                message=f'{(flights.index(flight)) + 1}. {flight}',
                random_id=random.randint(0, 2 ** 30),
                peer_id=user_id
            )

    def send_departures(self, user_id):
        """

        Отправка пользователю сообщений с городами, откуда есть рейсы
        :param user_id: Идентификатор пользователя (id пользователя вк)
        """
        n = 1
        for city in settings.FLIGHTS.keys():
            self.api.messages.send(
                message=f'{n}. {city}',
                random_id=random.randint(0, 2 ** 30),
                peer_id=user_id
            )
            n += 1

    def send_arrivals(self, user_id, state):
        """

        Отправка пользователю сообщений с городами, куда есть рейсы из города вылета
        :param user_id: Идентификатор пользователя (id пользователя вк)
        :param state: Состояние пользователя
        """
        departure_city = state.context['name_departure']
        n = 1
        for city in settings.FLIGHTS[departure_city].keys():
            self.api.messages.send(
                message=f'{n}. {city}',
                random_id=random.randint(0, 2 ** 30),
                peer_id=user_id
            )
            n += 1

    def send_data(self, user_id, state):
        """

        Отправка пользователю сообщений с полученными данными для проверки
        :param user_id: Идентификатор пользователя (id пользователя вк)
        :param state: Состояние пользователя
        """
        self.api.messages.send(
            message=f"Город отправления: {state.context['name_departure']}",
            random_id=random.randint(0, 2 ** 30),
            peer_id=user_id
        )
        self.api.messages.send(
            message=f"Город прибытия: {state.context['name_arrival']}",
            random_id=random.randint(0, 2 ** 30),
            peer_id=user_id
        )
        self.api.messages.send(
            message=f"Дата и время рейса: {state.context['user_flight']}",
            random_id=random.randint(0, 2 ** 30),
            peer_id=user_id
        )
        self.api.messages.send(
            message=f"Количество мест: {state.context['passengers']}",
            random_id=random.randint(0, 2 ** 30),
            peer_id=user_id
        )
        self.api.messages.send(
            message=f"Комментарий к заказу: {state.context['comment']}",
            random_id=random.randint(0, 2 ** 30),
            peer_id=user_id
        )


if __name__ == '__main__':
    config_loggers()
    vk_bot = Bot(group_id=MY_GROUP_ID, token=TOKEN)
    vk_bot.run()
