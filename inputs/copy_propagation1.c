void func(int x, int y) {
    int z;
    z = 1;
    x = x + y;
    y = z + x;
}

int main(void) {
    int y;
    int x, z;
    y = z;
    if (y == z) {
        x = 1;
    }

    x = x + y + z;
    printf("%d", x);
}
