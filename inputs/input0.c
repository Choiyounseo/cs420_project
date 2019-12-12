void func()
{
    return;
}

int add(int a, int b)
{
    int c;
    c = a + b;
    return c;
}

float mul(float a, float b)
{
    return a * b;
}

int main(void)
{
    int i;
    for (i = 0; i < 5; i ++) {
        printf ("%d\n", i + 1);
        printf ("%d\n", mul(2, i));

        int k;
        k = mul(2, i);
        if (k > 6) {
            printf ("Good!\n");
        }
    }

    func();

    printf ("%d\n", add((int)1.5, (int)(2 + 1.5)));

    int j;
    j = mul(3, 4);
    if (j > 10) {
        printf ("%d\n", j);
    }

    if (j < 10) {
        printf ("It's incorrect\n");
    }
}
