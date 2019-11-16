void func() {
    return;
}

int add(int a, int b) {
    int c;
    c = a + b;
    return c;
}

float mul(float a, float b) {
    return a * b;
}

int main(void) {
    int mark[2];
    func();
    printf("%d\n", add((int)1.5, (int)(2 + 1.5)));
    mul(3, 4);
}