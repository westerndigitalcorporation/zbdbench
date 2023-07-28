#!/usr/bin/bash
set -e

# Spdk pre-launch setup script for containerised environment

SPDK_DIR=/root/spdk
SPDK_FNAME="--filename=spdk_bdev"

spdk_fedora_bug_fix () {
	patch -p1  <<'EOF'
diff --git a/scripts/setup.sh b/scripts/setup.sh
index b4c2bec2c..43b6e7591 100755
--- a/scripts/setup.sh
+++ b/scripts/setup.sh
@@ -1,6 +1,7 @@
 #!/usr/bin/env bash

 set -e
+shopt -s nullglob extglob

 os=$(uname -s)

@@ -406,7 +407,7 @@ function configure_linux_pci() {
 }

 function cleanup_linux() {
-	shopt -s extglob nullglob
+#	shopt -s extglob nullglob
	dirs_to_clean=""
	dirs_to_clean="$(echo {/var/run,/tmp}/dpdk/spdk{,_pid}+([0-9])) "
	if [[ -d $XDG_RUNTIME_DIR && $XDG_RUNTIME_DIR != *" "* ]]; then
@@ -418,7 +419,7 @@ function cleanup_linux() {
		files_to_clean+="$(echo $dir/*) "
	done
	file_locks+=(/var/tmp/spdk_pci_lock*)
-	shopt -u extglob nullglob
+#	shopt -u extglob nullglob

	files_to_clean+="$(ls -1 /dev/shm/* \
		| grep -E '(spdk_tgt|iscsi|vhost|nvmf|rocksdb|bdevio|bdevperf|vhost_fuzz|nvme_fuzz|accel_perf|bdev_svc)_trace|spdk_iscsi_conns' || true) "
@@ -429,11 +430,11 @@ function cleanup_linux() {
		return 0
	fi

-	shopt -s extglob
+#	shopt -s extglob
	for fd_dir in $(echo /proc/+([0-9])); do
		opened_files+="$(readlink -e assert_not_empty $fd_dir/fd/* || true)"
	done
-	shopt -u extglob
+#	shopt -u extglob

	if [[ -z "$opened_files" ]]; then
		echo "Can't get list of opened files!"
@@ -614,7 +615,7 @@ function status_linux() {
	printf "%-6s %10s %8s / %6s\n" "node" "hugesize" "free" "total" >&2

	numa_nodes=0
-	shopt -s nullglob
+#	shopt -s nullglob
	for path in /sys/devices/system/node/node*/hugepages/hugepages-*/; do
		numa_nodes=$((numa_nodes + 1))
		free_pages=$(cat $path/free_hugepages)
@@ -627,7 +628,7 @@ function status_linux() {

		printf "%-6s %10s %8s / %6s\n" $node $huge_size $free_pages $all_pages
	done
-	shopt -u nullglob
+#	shopt -u nullglob

	# fall back to system-wide hugepages
	if [ "$numa_nodes" = "0" ]; then
EOF
}


cd $SPDK_DIR

# Lump all cmdline args into a single string
param_str="${@}"

# Tokenise the cmdline string for ' '
param_tokens=( $param_str)

for arg  in "${param_tokens[@]}";
do
	if [[ $arg == "--filename="* ]]; then
		# Strip '/dev' string out of '/dev/nvmeXnY' string
		#devname=$(sed 's+filename=/dev/+ +g' <<< $arg)
		echo "Replacing $arg(nvme dev) with $SPDK_FNAME(spdk bdev)"
		devname=$(sed 's/.*'dev'//' <<< $arg)
		#Replace the physical device name with spdk bdev name
		param_str=${param_str/$arg/$SPDK_FNAME}
	fi
done

# Edit the json file and update /dev/nvmeXnY as per phys nvme dev passed as cmdline arg
sed -i 's|\/nvme.*|'$devname'",|g' bdev_zoned_uring.json

# Kernel module required by SPDK
modprobe vfio-pci

# Fix Fedora related spdk 22.09 bug
DISTRO_FILE=/etc/redhat-release
if [ -f "$DISTRO_FILE" ]; then
    echo "Applying spdk bug fix patch for Fedora"
    spdk_fedora_bug_fix
fi

# Reserve hugepages. PCI_ALLOWED="none" as we are not using SPDK nvme driver
PCI_ALLOWED="none" ./scripts/setup.sh

exec fio $param_str

