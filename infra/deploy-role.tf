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

# Terraform plan refreshes every resource in the stack; read-only keeps the
# blast radius at zero while staying maintenance-free as the stack grows.
resource "aws_iam_role_policy_attachment" "deploy_readonly" {
  role       = aws_iam_role.deploy.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
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
