#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

void usage(const char *progname) {
    printf("Usage: %s <memory_size_in_MB>\n", progname);
    exit(EXIT_FAILURE);
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

    size_t mem_size = mem_size_mb * 1024 * 1024;

    char *memory = (char *)malloc(mem_size);
    if (memory == NULL) {
        perror("malloc failed");
        exit(EXIT_FAILURE);
    }

    printf("Allocated %zu MB of memory. Writing random values to all of it...\n", mem_size_mb);

    srand(time(NULL));
    size_t page_size = sysconf(_SC_PAGESIZE);

    // Mesurer le temps avant le remplissage
    clock_t start_time = clock();

    for (size_t i = 0; i < mem_size; i += page_size) {
        memory[i] = (char)(rand() % 2048);
    }

    // Mesurer le temps après le remplissage
    clock_t end_time = clock();

    double elapsed_time = (double)(end_time - start_time) / CLOCKS_PER_SEC;
    printf("Memory written. Time taken to fill memory: %.2f seconds.\n", elapsed_time);

    printf("Memory written. Blocking now.\n");

    while (1) {
        for (size_t i = 0; i < mem_size; i += page_size) {
            memory[i] = (char)(rand() % 2048);
        }
    }

    free(memory);

    return 0;
}
