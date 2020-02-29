from flask.cli import cli

from app import create_app
from app.models import Purchase,User,db,Category

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db':db, 'User':User,'Purchase':Purchase,'Category':Category}


