int main(void) {
    int i;
    int b, c, e;
    b = 1;

    int a, z;
    int x, y;
    x = 1;
    y = 2;
    a = 1 * 2;
    c = 1 + 2;
    e = 1 - 2;
    int __optimized_variable0;
    __optimized_variable0 = c+e;
    z = __optimized_variable0;
    for (i = 0; i < 10; i ++) {
        b = b * c + e;
        b = b * c + e;
        b = a * e;
        b = __optimized_variable0+b;
    }
}
