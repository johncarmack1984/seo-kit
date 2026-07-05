# CI deploy role, stormdeck-style: GitHub Actions assumes it via OIDC (no AWS
# keys in the repo), trust pinned to main on this repo. The site job uses the
# write statements; the infra job only plans (drift gate), covered by
# ReadOnlyAccess — applies stay local, per the my-infra plan-role convention.

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Pinned to the main ref. NOTE (learned on stormdeck): a job-level
    # `environment:` key rewrites the OIDC subject to repo:…:environment:…,
    # which this trust rejects — record deployments via the API instead.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:johncarmack1984/seo-kit:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "seo-kit-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.deploy_trust.json
}

# Scoped read set for the CI drift-gate plan: exactly the services this stack
# touches, and state access limited to this stack's own key. (The AWS-managed
# ReadOnlyAccess it replaces could read the whole account, including other
# stacks' terraform state.)
data "aws_iam_policy_document" "deploy_read" {
  statement {
    sid       = "SiteBucketRead"
    actions   = ["s3:Get*", "s3:List*"]
    resources = [aws_s3_bucket.site.arn, "${aws_s3_bucket.site.arn}/*"]
  }

  statement {
    sid       = "StateList"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::john-carmack-terraform-state"]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["seo-kit/*"]
    }
  }

  statement {
    sid       = "StateRead"
    actions   = ["s3:GetObject"]
    resources = ["arn:aws:s3:::john-carmack-terraform-state/seo-kit/*"]
  }

  statement {
    sid = "Route53Read"
    actions = [
      "route53:GetHostedZone",
      "route53:ListHostedZones",
      "route53:ListHostedZonesByName",
      "route53:ListResourceRecordSets",
      "route53:ListTagsForResource",
      "route53:GetChange",
    ]
    resources = ["*"]
  }

  statement {
    sid = "AcmRead"
    actions = [
      "acm:DescribeCertificate",
      "acm:ListCertificates",
      "acm:ListTagsForCertificate",
    ]
    resources = ["*"]
  }

  statement {
    sid = "CloudFrontRead"
    actions = [
      "cloudfront:GetDistribution",
      "cloudfront:GetDistributionConfig",
      "cloudfront:GetOriginAccessControl",
      "cloudfront:GetFunction",
      "cloudfront:DescribeFunction",
      "cloudfront:ListTagsForResource",
    ]
    resources = ["*"]
  }

  statement {
    # The provider data source looks the OIDC provider up BY URL, which lists
    # all providers before getting the match; list actions are not
    # resource-scopable.
    sid       = "IamList"
    actions   = ["iam:ListOpenIDConnectProviders"]
    resources = ["*"]
  }

  statement {
    sid = "SelfRead"
    actions = [
      "iam:GetRole",
      "iam:ListRolePolicies",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:GetOpenIDConnectProvider",
    ]
    resources = [
      "arn:aws:iam::735853783919:role/seo-kit-github-deploy",
      data.aws_iam_openid_connect_provider.github.arn,
    ]
  }
}

resource "aws_iam_role_policy" "deploy_read" {
  name   = "plan-scoped-read"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy_read.json
}

data "aws_iam_policy_document" "deploy_writes" {
  statement {
    sid       = "SyncSiteBucket"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]
  }

  statement {
    sid       = "InvalidateDistribution"
    actions   = ["cloudfront:CreateInvalidation"]
    resources = [aws_cloudfront_distribution.site.arn]
  }
}

resource "aws_iam_role_policy" "deploy_writes" {
  name   = "site-deploy-writes"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy_writes.json
}

output "deploy_role_arn" {
  value = aws_iam_role.deploy.arn
}
