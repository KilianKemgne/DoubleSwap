#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <pthread.h>

void usage(const char *progname) {
    printf("Usage: %s <memory_size_in_MB>\n", progname);
    exit(EXIT_FAILURE);
}

typedef struct {
    char *start;
    size_t size;
} ThreadData;

void *write_memory(void *arg) {
    ThreadData *data = (ThreadData *)arg;
    size_t page_size = sysconf(_SC_PAGESIZE);

    for (size_t i = 0; i < data->size; i += page_size) {
        data->start[i] = (char)(rand() % 2048);
    }

    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        usage(argv[0]);
    }

    size_t mem_size_mb = strtoul(argv[1], NULL, 10);
    if (mem_size_mb == 0) {
        printf("Invalid memory size. Must be a positive number.\n");
        usage(argv[0]);
    }

    size_t mem_size = mem_size_mb * 1024 * 1024 * 1024;

    char *memory = (char *)malloc(mem_size);
    if (memory == NULL) {
        perror("malloc failed");
        exit(EXIT_FAILURE);
    }

    printf("Allocated %zu GB of memory. Writing random values to all of it...\n", mem_size_mb);

    srand(time(NULL));

    clock_t start_time = clock();

    int num_threads = 6;
    pthread_t threads[num_threads];
    ThreadData thread_data[num_threads];

    size_t chunk_size = mem_size / num_threads;
    for (int i = 0; i < num_threads; i++) {
        thread_data[i].start = memory + i * chunk_size;
        thread_data[i].size = (i == num_threads - 1) ? (mem_size - i * chunk_size) : chunk_size;
        pthread_create(&threads[i], NULL, write_memory, &thread_data[i]);
    }

    for (int i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
    }

    clock_t end_time = clock();

    double elapsed_time = (double)(end_time - start_time) / CLOCKS_PER_SEC;
    printf("Memory written. Time taken to fill memory: %.2f seconds.\n", elapsed_time);

    printf("Memory written. Blocking now.\n");

    while (1) {
        sleep(1);
    }

    free(memory);

    return 0;
}
