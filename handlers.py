import re
import datetime
import settings
from ticket_maker import make_ticket

city_pattern = re.compile(r'^[А-Я]{1}[а-я]{2,10}$')
date_pattern = re.compile(r'(0[1-9]|[1-2][0-9]|3[0-1])(-0[1-9]|-1[1-2])(-2021)')
phone_pattern = re.compile(r'^([9]\d{9})$')


def handle_name_departure(text, context):
    match = re.match(city_pattern, text)
    if match:
        if text in settings.FLIGHTS.keys():
            context['name_departure'] = text
            context['data_error'] = None
            return True
        else:
            return False
    else:
        return False


def handle_name_arrival(text, context):
    match = re.match(city_pattern, text)
    if match:
        if text in settings.FLIGHTS[context['name_departure']].keys():
            context['name_arrival'] = text
            return True
        else:
            return False
    else:
        return False


def handle_date(text, context):
    match = re.match(date_pattern, text)
    if match:
        date = datetime.datetime.strptime(text, '%d-%m-%Y')
        if date > datetime.datetime.now():
            context['date'] = text
            return True
        else:
            return False
    else:
        return False


def controller(flights, city_departure, city_arrival, date, context):
    flights_list = []
    flight_timedelta = datetime.timedelta(hours=flights[city_departure][city_arrival][0])
    flight_time = datetime.datetime.strptime(date, '%d-%m-%Y') + flight_timedelta
    if city_departure == 'Москва' and city_arrival == 'Париж':
        n = 0
        i = 0
        while n < 5:
            flight_date = flight_time + datetime.timedelta(days=i)
            if datetime.datetime.weekday(flight_date) == 0 or datetime.datetime.weekday(flight_date) == 3:
                flights_list.append(flight_date.strftime('%d-%m-%Y %H:%M'))
                n += 1
            i += 1
    elif city_departure == 'Москва' and city_arrival == 'Калифорния':
        n = 0
        i = 0
        while n < 5:
            flight_date = flight_time + datetime.timedelta(days=i)
            if flight_date.day == 10 or flight_date.day == 20:
                flights_list.append(flight_date.strftime('%d-%m-%Y %H:%M'))
                n += 1
            i += 1
    else:
        for i in range(5):
            flight_date = flight_time + datetime.timedelta(days=i)
            flights_list.append(flight_date.strftime('%d-%m-%Y %H:%M'))
    context['flights'] = flights_list


def handle_flights(text, context):
    if not text or not text.isdigit():
        return False
    elif int(text) > len(context['flights']):
        return False
    else:
        index = int(text) - 1
        context['user_flight'] = context['flights'][index]
        return True


def handle_passengers_count(text, context):
    if not text or not text.isdigit():
        return False
    elif int(text) > 5:
        return False
    else:
        context['passengers'] = text
        return True


def handle_comment(text, context):
    context['comment'] = text
    return True


def handle_data(text, context):
    if not text:
        return False
    elif text.lower() == 'нет':
        context['data_error'] = 'Попробуйте ещё раз...'
        return False
    elif text.lower() == 'да':
        return True
    else:
        return False


def handle_phone(text, context):
    match = re.match(phone_pattern, text)
    if match:
        context['phone'] = text
        return True
    else:
        return False


def get_ticket(text, context):
    return make_ticket(
        departure=context['name_departure'],
        arrival=context['name_arrival'],
        date=context['user_flight'],
        sits=context['passengers'],
        comment=context['comment'],
        phone=context['phone']
    )
