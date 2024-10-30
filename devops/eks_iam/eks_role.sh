# Create a policy document with both CreateVolume and CreateTags permissions
cat <<EOF > ebs-full-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateVolume",
                "ec2:DeleteVolume",
                "ec2:AttachVolume",
                "ec2:DetachVolume",
                "ec2:DescribeVolumes",
                "ec2:DescribeInstances",
                "ec2:CreateTags",
                "ec2:DeleteTags"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Apply to your node role
aws iam put-role-policy \
  --role-name eksctl-my-minimal-cluster-nodegrou-NodeInstanceRole-FRVzJIIWpMmC \
  --policy-name ebs-full-access \
  --policy-document file://ebs-full-policy.json