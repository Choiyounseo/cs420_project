void func(int x, int y) {
    int z;
    z = 1;
    x = x + y;
    y = z + x;
}

int main(void) {
    int a;
    int b;
    int c;
    int e, f;
    int g, h;
    int d[10];
    a = 1;
    d[0] = 1;
    d[1] = 2;
    d[2] = 3;
    for(b = 0; b < 10; b ++) {
        int a;
        a = 2;
        d[2] = 5;
    }
    c = 1;
    b = 1;
    int __optimized_variable0;
    __optimized_variable0 = d[0];
    e = __optimized_variable0;
    g = __optimized_variable0;
    f = d[1];
    h = d[2];
}
