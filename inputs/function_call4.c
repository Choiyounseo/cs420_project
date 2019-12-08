void test(void) {
    int b;
    return 3;
}

int main(void) {
    int a;
    a = 2;
    int c;
    c = test() + test();
    printf("%d\n", c);
    printf("test is pass");
}