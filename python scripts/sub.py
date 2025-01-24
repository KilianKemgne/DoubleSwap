import threading
import paho.mqtt.client as mqtt
import time

BROKER = "localhost"
PORT = 1883
MESSAGE_SIZE = 1024 * 1024
TOTAL_SIZE = 1 * 1024 * 1024 * 1024
NUM_MESSAGES = TOTAL_SIZE // MESSAGE_SIZE
NUM_PUBLISHERS = 100
NUM_SUBSCRIBERS = 100

def generate_time_based_message(size):
    current_time_ns = str(time.time_ns())
    message = current_time_ns.ljust(size, "0")[:size]
    return message


def subscriber(client_id, topic):
    def on_message(client, userdata, message):
        print(f"[Subscriber-{client_id}] Message reçu sur {message.topic}: taille {len(message.payload)}")

    client = mqtt.Client(client_id=f"subscriber-{client_id}", clean_session=False)
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.subscribe(topic, qos=1)
    print(f"[Subscriber-{client_id}] Abonné au topic {topic}")
    client.loop_forever()


def publisher(client_id, topic, num_messages):
    client = mqtt.Client(client_id=f"publisher-{client_id}", clean_session=False)
    client.connect(BROKER, PORT, 60)

    for i in range(num_messages):
        message = generate_time_based_message(MESSAGE_SIZE)
        client.publish(topic, message, qos=1, retain=True)
        print(f"[Publisher-{client_id}] Message {i + 1}/{num_messages} publié sur {topic}")
        time.sleep(0.01)

    client.disconnect()
    print(f"[Publisher-{client_id}] Déconnecté")


subscriber_threads = []
for i in range(NUM_SUBSCRIBERS):
    topic = f"test/topic/"
    # topic = f"test/topic/{i}"
    thread = threading.Thread(target=subscriber, args=(i, topic))
    thread.daemon = True
    subscriber_threads.append(thread)
    thread.start()

time.sleep(2)

publisher_threads = []
for i in range(NUM_PUBLISHERS):
    # topic = f"test/topic/{i}"
    topic = f"test/topic/"
    thread = threading.Thread(target=publisher, args=(i, topic, NUM_MESSAGES))
    thread.daemon = True
    publisher_threads.append(thread)
    thread.start()

for thread in publisher_threads:
    thread.join()

print("Tous les messages ont été publiés.")
