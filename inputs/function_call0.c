int identity(int a) {
    return a;
}

int main(void) {
    int a;
    a = identity(5);
    printf ("Identity : ");
    printf ("%d", a);
    printf (", Excepted : ");
    printf ("%d\n", 5);

    int i;
    int count = 5;
    int sum, sum2;
    sum = 0;
    sum2 = 0;

    for (i = 1; i < count; i ++) {
        sum = sum + identity(i);
        sum2 = sum2 + identity(i) + identity(i);
    }

    printf ("%d\n", sum);
    printf ("%d\n", sum2);

    if (sum2 > sum) {
        printf ("It's correct!\n");
    }

    if (sum2 < sum) {
        printf ("It's incorrect!\n");
    }
}
