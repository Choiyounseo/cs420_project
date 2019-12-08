int main(void)
{
    int count, i, sum;

    count = 4;
    sum = 0;

    for (i = 0; i < count; i++)
    {
    	if(i <1)
    	{
    		int sum;
    		sum = 1;
    	}
    	printf("%d\n",sum);
    	sum = sum + 1;
    }
    printf("%d\n", sum);
}
