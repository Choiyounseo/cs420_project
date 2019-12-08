int main(void) {
    int a,b,c;
    int d[4];
    d[2] = 1;
    a = d[2];
    b = a;
    if(a > 0){
    	c = a;
    	int a,b;
    	a = c;
    	b = a;
    	a = a + 1;
    	c = a;
    }
    c = b;

    printf("%d\n",b);
}