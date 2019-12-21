void change(int *array, int index) {
	array[index] = 1;
	return;
}

int main(void) {
	int a[1];

	a[0] = 0;
	printf("a[0] is %d\n", a[0]);

	change(a, 0);
	printf("now a[0] is %d\n", a[0]);

	printf("Done!\n");
}
