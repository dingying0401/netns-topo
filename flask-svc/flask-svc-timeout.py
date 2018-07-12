from flask import Flask
from flask import request
import os
import time


application = Flask(__name__)


@application.route("/")
def hello():
    ra = request.remote_addr
    if ra == "10.0.0.9":
        time.sleep(6)
    return "%s: Hello World! :%s :%s\n" % (os.popen('ip netns identify').read().strip(), request.remote_addr, request.headers.get('X-Forwarded-For')), 300


if __name__ == "__main__":
    application.run(host='0.0.0.0', port=80)
