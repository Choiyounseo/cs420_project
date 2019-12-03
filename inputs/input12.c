int main(void) {
    int i, sum, a;

    sum = 0;
    a = 1;

    for (i = 0; i < 2; i++) {
    	int sum;
    	a = 2;
    	if(i < 1){
        	sum = 999;
        }
        if(i > 0){
            sum = sum + 1;	
        }			
    	printf("%d\n",sum);
    }
    printf("%d\n", sum);
}
