eksctl create nodegroup \
  --cluster my-minimal-cluster \
  --name ng-t2-medium \
  --node-type t2.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 4 \
  --node-private-networking \
  --region us-east-2

# max pods:
# t2.micro  4
# t2.medium  17

#eksctl create nodegroup \
#  --cluster <your-cluster-name> \
#  --name <nodegroup-name> \
#  --node-type <instance-type> \
#  --nodes <desired-capacity> \
#  --nodes-min <minimum-capacity> \
#  --nodes-max <maximum-capacity> \
#  --node-private-networking \
#  --region <region>