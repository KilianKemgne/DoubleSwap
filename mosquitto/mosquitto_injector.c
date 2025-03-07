#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <time.h>
#include <MQTTClient.h>

#define BROKER "tcp://localhost:1883"
#define TOPIC "test/topic"
#define CLIENT_ID_PREFIX "client"
#define MESSAGE_SIZE 1048576
#define TOTAL_SIZE (5368709120)
#define NUM_MESSAGES (TOTAL_SIZE / MESSAGE_SIZE)
#define NUM_PUBLISHERS 3
#define NUM_SUBSCRIBERS 1

// Fonction pour générer un message basé sur le temps
void generate_time_based_message(char *message, size_t size) {
    if (size) {
        --size;
        memset(message, 'K', size);
        message[size] = '\0';
    }
}

// Callback appelée lorsqu'un message est reçu
void on_message(void *context, char *topicName, int topicLen, MQTTClient_message *message) {
    printf("[Subscriber-%s] Message reçu sur %s: taille %d\n", (char *)context, topicName, message->payloadlen);
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
}

// Fonction pour le subscriber
void *subscriber(void *arg) {
    int client_id = *(int *)arg;
    char client_id_str[32];
    snprintf(client_id_str, sizeof(client_id_str), "%s-subscriber-%d", CLIENT_ID_PREFIX, client_id);

    MQTTClient client;
    MQTTClient_create(&client, BROKER, client_id_str, MQTTCLIENT_PERSISTENCE_NONE, NULL);
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
    conn_opts.keepAliveInterval = 60;
    conn_opts.cleansession = 0;

    if (MQTTClient_connect(client, &conn_opts) != MQTTCLIENT_SUCCESS) {
        fprintf(stderr, "[Subscriber-%d] Échec de la connexion au broker\n", client_id);
        return NULL;
    }

    printf("[Subscriber-%d] Abonné au topic %s\n", client_id, TOPIC);
    MQTTClient_subscribe(client, TOPIC, 2);

    MQTTClient_setCallbacks(client, client_id_str, NULL, on_message, NULL);

    sleep(1); // Garder le subscriber actif

    MQTTClient_disconnect(client, 1000);
    MQTTClient_destroy(&client);
    return NULL;
}

// Fonction pour le publisher
void *publisher(void *arg) {
    int client_id = *(int *)arg;
    char client_id_str[32];
    snprintf(client_id_str, sizeof(client_id_str), "%s-publisher-%d", CLIENT_ID_PREFIX, client_id);

    MQTTClient client;
    MQTTClient_create(&client, BROKER, client_id_str, MQTTCLIENT_PERSISTENCE_NONE, NULL);
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
    conn_opts.keepAliveInterval = 60;
    conn_opts.cleansession = 0;

    if (MQTTClient_connect(client, &conn_opts) != MQTTCLIENT_SUCCESS) {
        fprintf(stderr, "[Publisher-%d] Échec de la connexion au broker\n", client_id);
        return NULL;
    }

    // Calculer le nombre de messages à publier par publisher
    int messages_per_publisher = NUM_MESSAGES / NUM_PUBLISHERS;
    int start_index = client_id * messages_per_publisher;
    int end_index = (client_id == NUM_PUBLISHERS - 1) ? NUM_MESSAGES : start_index + messages_per_publisher;

    char message[MESSAGE_SIZE + 1];
    for (int i = start_index; i < end_index; i++) {
        generate_time_based_message(message, MESSAGE_SIZE);
        MQTTClient_message pubmsg = MQTTClient_message_initializer;
        pubmsg.payload = message;
        pubmsg.payloadlen = MESSAGE_SIZE;
        pubmsg.qos = 2;
        pubmsg.retained = 0;

        if (MQTTClient_publishMessage(client, TOPIC, &pubmsg, NULL) != MQTTCLIENT_SUCCESS) {
            fprintf(stderr, "[Publisher-%d] Échec de la publication du message %d\n", client_id, i + 1);
        } else {
            printf("[Publisher-%d] Message %d/%d publié sur %s\n", client_id, i + 1, NUM_MESSAGES, TOPIC);
        }

        usleep(10000); // Attendre 10 ms entre les messages
    }

    MQTTClient_disconnect(client, 1000);
    MQTTClient_destroy(&client);
    printf("[Publisher-%d] Déconnecté\n", client_id);
    return NULL;
}

int main() {
    pthread_t subscriber_threads[NUM_SUBSCRIBERS];
    pthread_t publisher_threads[NUM_PUBLISHERS];
    int subscriber_ids[NUM_SUBSCRIBERS];
    int publisher_ids[NUM_PUBLISHERS];

    // Capturer le temps de début
    struct timespec start_time, end_time;
    clock_gettime(CLOCK_MONOTONIC, &start_time);

    // Démarrer les subscribers
    for (int i = 0; i < NUM_SUBSCRIBERS; i++) {
        subscriber_ids[i] = i;
        pthread_create(&subscriber_threads[i], NULL, subscriber, &subscriber_ids[i]);
    }

    sleep(2); // Attendre que les subscribers soient prêts

    // Démarrer les publishers
    for (int i = 0; i < NUM_PUBLISHERS; i++) {
        publisher_ids[i] = i;
        pthread_create(&publisher_threads[i], NULL, publisher, &publisher_ids[i]);
    }

    // Attendre que les publishers terminent
    for (int i = 0; i < NUM_PUBLISHERS; i++) {
        pthread_join(publisher_threads[i], NULL);
    }

    // Capturer le temps de fin
    clock_gettime(CLOCK_MONOTONIC, &end_time);

    // Calculer la durée totale
    long duration_seconds = end_time.tv_sec - start_time.tv_sec;
    long duration_nanoseconds = end_time.tv_nsec - start_time.tv_nsec;
    if (duration_nanoseconds < 0) {
        duration_seconds--;
        duration_nanoseconds += 1000000000L;
    }

    printf("Tous les messages ont été publiés.\n");
    printf("Temps total d'injection : %ld secondes et %ld nanosecondes\n", duration_seconds, duration_nanoseconds);

    return 0;
}