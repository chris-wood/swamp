data:
	dd bs=1 count=32768 if=/dev/urandom of=random.bin

proto:
	protoc --python_out=$(DST_DIR) swamp.proto