int main(void)
{
    int count, i, sum;
    float average;

    count = 4;
    sum = 0;

    for (i = 0; i < count; i++)
    {
        sum = sum + i * 30;
    }

    average = sum / count;
    printf("%f\n", average);
}
