import configparser
from flask import Flask
from wptdash.database import db
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

DEFAULTS = { 'WPTDASH_DB_HOST': 'localhost' }
CONFIG = configparser.ConfigParser(defaults=DEFAULTS)
CONFIG.readfp(open(r'config.txt'))
WPTDASH_DB = CONFIG.get('postgresql', 'WPTDASH_DB')
WPTDASH_DB_USER = CONFIG.get('postgresql', 'WPTDASH_DB_USER')
WPTDASH_DB_PASS = CONFIG.get('postgresql', 'WPTDASH_DB_PASS')
WPTDASH_DB_HOST = CONFIG.get('postgresql', 'WPTDASH_DB_HOST')

# This is here to not-break existing installations

if WPTDASH_DB_HOST == "":
    WPTDASH_DB_HOST = "localhost"

WPTDASH_DB_URI = 'postgresql://%s:%s@%s/%s' % (WPTDASH_DB_USER,
                                               WPTDASH_DB_PASS,
                                               WPTDASH_DB_HOST,
                                               WPTDASH_DB)

app = Flask(__name__)
app.config.update(dict(
    DEBUG=True,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_DATABASE_URI=WPTDASH_DB_URI
))
app.config.from_envvar('WPTDASH_SETTINGS', silent=True)

db.init_app(app)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
