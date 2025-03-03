#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <hiredis/hiredis.h>
#include <pthread.h>

#define MAX_THREADS 10
#define BATCH_SIZE 100
#define VALUE_SIZE 4094
#define KEY_SIZE 32
#define PROGRESS_INTERVAL 200000

typedef struct {
    int thread_id;
    int nombreDeCles;
    const char *hostname;
    int port;
} ThreadArgs;

int total_injected = 0;
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;

void generateRandomString(char *str, size_t size) {
    const char charset[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    if (size) {
        --size;
        for (size_t n = 0; n < size; n++) {
            int key = rand() % (int)(sizeof(charset) - 1);
            str[n] = charset[key];
        }
        str[size] = '\0';
    }
}

void generateRandomValue(char *str, size_t size) {
    if (size) {
        --size;
        memset(str, 'K', size);
        str[size] = '\0';
    }
}

void *injectKeys(void *args) {
    ThreadArgs *threadArgs = (ThreadArgs *)args;
    int thread_id = threadArgs->thread_id;
    int nombreDeCles = threadArgs->nombreDeCles;
    const char *hostname = threadArgs->hostname;
    int port = threadArgs->port;

    redisContext *c;
    struct timeval timeout = { 1, 500000 };
    c = redisConnectWithTimeout(hostname, port, timeout);
    if (c == NULL || c->err) {
        if (c) {
            fprintf(stderr, "Thread %d: Connection error: %s\n", thread_id, c->errstr);
            redisFree(c);
        } else {
            fprintf(stderr, "Thread %d: Connection error: can't allocate redis context\n", thread_id);
        }
        pthread_exit(NULL);
    }
    
    printf("Thread %d: Connexion Redis établie\n", thread_id);

    int keysPerThread = nombreDeCles / MAX_THREADS;
    int start = thread_id * keysPerThread;
    int end = (thread_id == MAX_THREADS - 1) ? nombreDeCles : start + keysPerThread;

    for (int i = start; i < end; i += BATCH_SIZE) {
        for (int j = 0; j < BATCH_SIZE && (i + j) < end; j++) {
            char cle[KEY_SIZE];
            char valeur[VALUE_SIZE];
            generateRandomString(cle, sizeof(cle));
            generateRandomValue(valeur, sizeof(valeur));
            redisAppendCommand(c, "SET %s %s", cle, valeur);
        }

        for (int j = 0; j < BATCH_SIZE && (i + j) < end; j++) {
            redisReply *reply;
            redisGetReply(c, (void **)&reply);
            if (reply == NULL) {
                fprintf(stderr, "Thread %d: Erreur lors de l'injection de la clé\n", thread_id);
                redisFree(c);
                pthread_exit(NULL);
            }
            freeReplyObject(reply);

            pthread_mutex_lock(&mutex);
            total_injected++;
            if (total_injected % PROGRESS_INTERVAL == 0) {
                printf("%d clés-valeurs injectées...\n", total_injected);
            }
            pthread_mutex_unlock(&mutex);
        }
    }

    printf("Thread %d: Connexion Redis fermée\n", thread_id);
    redisFree(c);
    pthread_exit(NULL);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <nombre_de_cles>\n", argv[0]);
        exit(1);
    }

    int nombreDeCles = atoi(argv[1]);
    if (nombreDeCles <= 0) {
        fprintf(stderr, "Le nombre de clés doit être un entier positif.\n");
        exit(1);
    }

    srand(time(NULL));

    const char *hostname = "127.0.0.1";
    int port = 6379;

    pthread_t threads[MAX_THREADS];
    ThreadArgs threadArgs[MAX_THREADS];

    struct timespec start_time, end_time;
    clock_gettime(CLOCK_MONOTONIC, &start_time);

    for (int i = 0; i < MAX_THREADS; i++) {
        threadArgs[i].thread_id = i;
        threadArgs[i].nombreDeCles = nombreDeCles;
        threadArgs[i].hostname = hostname;
        threadArgs[i].port = port;

        if (pthread_create(&threads[i], NULL, injectKeys, (void *)&threadArgs[i])) {
            fprintf(stderr, "Erreur lors de la création du thread %d\n", i);
            exit(1);
        }
    }

    for (int i = 0; i < MAX_THREADS; i++) {
        pthread_join(threads[i], NULL);
    }

    clock_gettime(CLOCK_MONOTONIC, &end_time);

    double time_taken = (end_time.tv_sec - start_time.tv_sec) * 1e9;
    time_taken = (time_taken + (end_time.tv_nsec - start_time.tv_nsec)) * 1e-9;

    printf("%d clés-valeurs ont été injectées avec succès.\n", nombreDeCles);
    printf("Temps total d'injection : %.6f secondes\n", time_taken);

    pthread_mutex_destroy(&mutex);

    return 0;
}
