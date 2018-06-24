from flask import Flask
import os


application = Flask(__name__)


@application.route("/")
def hello():
    return "%s: Hello World!" % os.popen('ip netns identify').read().strip()


if __name__ == "__main__":
    application.run(host='0.0.0.0', port=80)
