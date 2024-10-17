MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="==BOUNDARY=="

--==BOUNDARY==
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
/etc/eks/bootstrap.sh my-minimal-cluster --use-max-pods false --kubelet-extra-args '--max-pods=20'

--==BOUNDARY==--
