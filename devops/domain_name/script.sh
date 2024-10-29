aws acm request-certificate \
  --domain-name "*.chenfei-demo.com" \
  --validation-method DNS \
  --subject-alternative-names "chenfei-demo.com"

#{
#    "CertificateArn": "arn:aws:acm:us-east-2:241533164431:certificate/7a4c6261-c64c-4370-8470-df6adb47e585"
#}


cat <<EOF > external-dns-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "route53:ChangeResourceRecordSets"
            ],
            "Resource": [
                "arn:aws:route53:::hostedzone/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "route53:ListHostedZones",
                "route53:ListResourceRecordSets"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name ExternalDNSPolicy \
    --policy-document file://external-dns-policy.json



# Replace with your AWS account ID and cluster name
eksctl create iamserviceaccount \
    --cluster=my-minimal-cluster \
    --namespace=kube-system \
    --name=external-dns \
    --attach-policy-arn=arn:aws:iam::241533164431:policy/ExternalDNSPolicy \
    --override-existing-serviceaccounts \
    --approve


# Get your cluster's OIDC provider URL
export OIDC_URL=$(aws eks describe-cluster --name my-minimal-cluster --query "cluster.identity.oidc.issuer" --output text | sed 's/https:\/\///')

# Create the OIDC provider
eksctl utils associate-iam-oidc-provider \
    --cluster my-minimal-cluster \
    --approve