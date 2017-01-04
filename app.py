from __future__ import print_function
import os
import sys
import json

import requests
import string
from time import mktime
from datetime import datetime
from flask import Flask, request

import feedparser

app = Flask(__name__)

#util function to get the time of a post from now
def get_time_from_now(struct_time):
    dt = datetime.fromtimestamp(mktime(struct_time))
    dif = datetime.utcnow() - dt
    m, s = divmod(dif.days * 86400 + dif.seconds, 60)
    h, m = divmod(m, 60)
    return "%d hours %d minutes %s seconds ago" % (h, m, s)

@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


# endpoint for processing incoming PuSH feed events
@app.route('/feed', methods=['POST'])
def webhook_feed():
    log("hello")
    request.get_data()
    log(request.data)

    return "ok", 200

# endpoint for processing incoming messaging events
@app.route('/', methods=['POST'])
def webhook():

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    if message_text == "flights":
                        res = []
                        try:
                            d = feedparser.parse('http://feeds.feedburner.com/TheFlightDeal?format=xml')
                            for entry in d['entries']:
                                if 'san francisco' in entry['title'].lower() or 'los angeles' in entry['title'].lower():
                                    time_from_now = get_time_from_now(entry['published_parsed'])
                                    res.append("\n%s\n%s\n%s\n" % (entry['title'], entry['feedburner_origlink'], time_from_now))
                            if len(res) == 0:
                                res = ["<No results>"]
                        except Exception as e:
                            res = ["An error has occurred in parsing."]
                        #log(res)
                        for text in res:
                            send_text(sender_id, text)

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200


def send_text(recipient_id, message_text):
    message_data = {'text': message_text}
    #log("sending text message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))
    post_message(recipient_id, message_data)

# TODO: send detailed itin info when needed
def send_detailed_info(recipient_id, message_arg):
    pass

def post_message(recipient_id, message_data):
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": message_data
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log("Error")
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
