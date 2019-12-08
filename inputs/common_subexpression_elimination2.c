int main(void) {
    int i;
    int b, c, e;
    b = 1;
    c = 3;
    e = 4;

    int a, z;
    int x, y;
    x = 1;
    y = 2;
    a = x * y;
    z = c + e;
    for (i = 0; i < 10; i ++) {
        b = b * c + e;
        b = b * c + e;
        b = a * e;
        b = b + c + e;
    }
}
