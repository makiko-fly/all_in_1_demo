kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: readonly-user-token
  namespace: kubernetes-dashboard
  annotations:
    kubernetes.io/service-account.name: readonly-user
type: kubernetes.io/service-account-token
EOF


kubectl get secret readonly-user-token -n kubernetes-dashboard -o jsonpath='{.data.token}' | base64 --decode