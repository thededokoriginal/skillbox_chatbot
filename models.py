from pony.orm import Database, Required, Json
from settings import DB_CONFIG

db = Database()
db.bind(**DB_CONFIG)


class UserStates(db.Entity):
    user_id = Required(str, unique=True)
    scenario_name = Required(str)
    step_name = Required(str)
    context = Required(Json)


class UsersData(db.Entity):
    departure = Required(str)
    arrival = Required(str)
    date = Required(str)
    sits = Required(str)
    comment = Required(str)


db.generate_mapping(create_tables=True)
