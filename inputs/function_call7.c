int sum(int num) {
    int tmp;
    if (num > 0) {
        tmp = num - 1;
        num = num + sum(tmp);
    }
    return num;
}

int main(void) {
    int a;
    a = sum(50);
    printf("%d\n", a);
}
