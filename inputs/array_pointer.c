void change(int *array, int index) {
	array[index] = 1;
	return;
}

int main(void) {
	int a[1];

	a[0] = 0;
	printf("currently, %d\n", a[0]);

	printf("Changes.. \n");

	change(a, 0);
	printf("now, %d\n", a[0]);

	printf("Done!\n");
}
