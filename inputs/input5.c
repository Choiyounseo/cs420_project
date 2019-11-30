int main(void) {
    int i, j;
    int sum;
    sum = 0;
    for (i = 0; i < 5; i++) {
        for (j = 0; j < 5; j ++) {
            printf("%d %d\n", i, j);
            sum = sum + i * 5 + j;
        }
    }

    printf("%d\n", sum);
}
