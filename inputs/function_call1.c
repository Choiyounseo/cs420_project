int sum(int num) {
	int num2;
	num2 = 0;
    if (num > 0) {
        num2 = sum(num-1);
        num2 = num2 + num;
    }
    return num2;
}

int main(void) {
    int a;
    a = sum(5);
    printf ("%d\n", a);
}
