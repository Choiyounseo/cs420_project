int main(void) {
    int a;
    int b;
    int c[4];
    a = 1;
    b = 1;
    b++;
    c[0] = 3;
    a = a * b / a;
    b = a + b * a;
    printf("woohoo\n");
    printf("%d\n%d\n", a, b);
    printf("%d\n", c[0]);
}