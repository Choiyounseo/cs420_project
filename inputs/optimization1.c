int main(void) {
    int i;
    int b, c, e;
    b = 1;

    int a, z;
    int x, y;
    x = 1;
    y = 2;
    a = x * y;
    c = x + y;
    e = x - y;
    z = c + e;
    for (i = 0; i < 10; i ++) {
        b = b * c + e;
        b = b * c + e;
        b = a * e;
        b = c + e + b;
    }
}
