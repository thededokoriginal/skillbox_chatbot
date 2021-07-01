import unittest
from copy import deepcopy
from unittest.mock import patch, Mock
from pony.orm import db_session, rollback
from vk_api.bot_longpoll import VkBotMessageEvent
from bot import Bot
import settings
import datetime
from ticket_maker import make_ticket

date = datetime.datetime.today() + datetime.timedelta(days=1)
date_formatted = date.strftime('%d-%m-%Y')


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()
    return wrapper


class BotTest(unittest.TestCase):
    RAW_EVENT = {'type': 'message_new',
                 'object': {'date': 1615913728,
                            'from_id': 50124000,
                            'id': 335,
                            'out': 0,
                            'peer_id': 50124000,
                            'text': '1',
                            'conversation_message_id': 235,
                            'fwd_messages': [],
                            'important': False,
                            'random_id': 0,
                            'attachments': [],
                            'is_hidden': False},
                 'group_id': 202554920,
                 'event_id': 'c155193849aea8e9e00d7f91b6eb478529ea7541'}

    def test_run(self):
        count = 3
        obj = {}
        events = [obj] * count
        long_poller_mock = Mock(return_value=events)
        long_poller_listen_mock = Mock()
        long_poller_listen_mock.listen = long_poller_mock
        long_poller_mock.type = Mock()
        with patch('bot.vk_api.VkApi'):
            with patch('bot.VkBotLongPoll', return_value=long_poller_listen_mock):
                bot = Bot(group_id='', token='')
                bot.got_event = Mock()
                bot.send_ticket = Mock()
                bot.run()
                bot.got_event.assert_called()
                bot.got_event.assert_any_call(event=obj)
                assert bot.got_event.call_count == count

    INPUTS = [
        'Привет',
        '/ticket',
        'Москва',
        'Прага',
        f'{date_formatted}',
        '1',
        '1',
        'comment',
        'да',
        '9991234567'
    ]
    EXPECTED_OUTPUTS = [
        settings.HELP,
        settings.SCENARIOS['get_ticket']['steps']['step_1']['text'],
        settings.SCENARIOS['get_ticket']['steps']['step_2']['text'],
        settings.SCENARIOS['get_ticket']['steps']['step_3']['text'],
        f'1. {date.strftime("%d-%m-%Y")} 14:00',
        f'2. {(date + datetime.timedelta(days=1)).strftime("%d-%m-%Y")} 14:00',
        f'3. {(date + datetime.timedelta(days=2)).strftime("%d-%m-%Y")} 14:00',
        f'4. {(date + datetime.timedelta(days=3)).strftime("%d-%m-%Y")} 14:00',
        f'5. {(date + datetime.timedelta(days=4)).strftime("%d-%m-%Y")} 14:00',
        settings.SCENARIOS['get_ticket']['steps']['step_4']['text'],
        settings.SCENARIOS['get_ticket']['steps']['step_5']['text'],
        settings.SCENARIOS['get_ticket']['steps']['step_6']['text'],
        f'Город отправления: Москва ',
        f'Город прибытия: Прага',
        f'Дата и время рейса: {date.strftime("%d-%m-%Y")} 14:00',
        f'Количество мест: 1',
        f'Комментарий к заказу: comment',
        settings.SCENARIOS['get_ticket']['steps']['step_7']['text'],
        settings.SCENARIOS['get_ticket']['steps']['step_8']['text'],
        settings.SCENARIOS['get_ticket']['steps']['step_9']['text'].format(phone='9991234567')
    ]

    @isolate_db
    def test_got_event(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock
        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['text'] = input_text
            events.append(VkBotMessageEvent(event))
        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)
        with patch('bot.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.send_ticket = Mock()
            bot.run()
        assert send_mock.call_count == (len(self.INPUTS) + 10)
        real_outputs = []
        for call in send_mock.call_args_list:
            real_outputs.append(call[1]['message'])
        assert len(real_outputs) == len(self.EXPECTED_OUTPUTS)

    def test_ticket_maker(self):
        ticket_file = make_ticket('test', 'test', 'test', 'test', 'test', 'test')
        with open('files/ticket_example.jpg', 'rb') as expected_file:
            expected_bytes = expected_file.read()
        assert ticket_file.read() == expected_bytes


if __name__ == '__main__':
    unittest.main()
