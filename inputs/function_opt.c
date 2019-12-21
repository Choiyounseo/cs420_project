void donothing(int a) {
	int x, y;
	x = 0;
	y = x + 3;
	y = a + 3;
	return;
}

int main(void) {
	donothing(2);

	printf("Done!\n");
}
